#!/usr/bin/env python3
"""
Pipeline Ghost Boats — Mode SAR seul.
Détecte les signatures radar au large de La Réunion.
"""

import json
import math
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime, timezone

import numpy as np
import rasterio
from rasterio.windows import Window
from scipy.ndimage import uniform_filter, median_filter
from scipy.spatial import cKDTree

# ============================================================
# CONFIGURATION
# ============================================================
SAFE_DIR = Path('/home/gleaphe/Desktop/NAVY/sar_data/S1D_IW_GRDH_1SDV_20261008T014642_20261008T014707_004917_009431_8659_COG.SAFE')

REUNION_LAT = -21.12
REUNION_LON = 55.53

RADIUS_KM = 150
MIN_DIST_REU_KM = 30               # Rayon île = 30 km
KM_PER_DEG_LAT = 111.0

CFAR_GUARD = 2
CFAR_TRAIN = 5
CFAR_THRESHOLD_FACTOR = 5.0
MIN_VESSEL_PIXELS = 3
CLUSTER_RADIUS_PX = 5
MIN_INTENSITY_RATIO = 2.5          # img > mean_local * 2.5

OUTPUT_FILE = Path('/home/gleaphe/Desktop/NAVY/ghost_boats.json')


# ============================================================
# GÉOLOCALISATION
# ============================================================
class SarGeolocator:
    def __init__(self, safe_dir, polarization='vv'):
        safe_dir = Path(safe_dir)
        ann_files = list(safe_dir.glob(f'annotation/s1*-{polarization}-*.xml'))
        if not ann_files:
            raise FileNotFoundError(f"Annotation {polarization} introuvable")

        tree = ET.parse(ann_files[0])
        root = tree.getroot()

        self.points = []
        for pt in root.iter('geolocationGridPoint'):
            line = int(pt.find('line').text)
            pixel = int(pt.find('pixel').text)
            lat = float(pt.find('latitude').text)
            lon = float(pt.find('longitude').text)
            self.points.append((pixel, line, lat, lon))

        self.pixels = sorted(set(p[0] for p in self.points))
        self.lines = sorted(set(p[1] for p in self.points))
        self._grid = {(p, l): (lat, lon) for (p, l, lat, lon) in self.points}

    def _find_index(self, arr, val):
        for i in range(len(arr) - 1):
            if arr[i] <= val <= arr[i + 1]:
                return i
        return len(arr) - 2

    def pixel_to_latlon(self, pixel, line):
        i_pix = self._find_index(self.pixels, pixel)
        i_lin = self._find_index(self.lines, line)
        p0 = self.pixels[i_pix]
        p1 = self.pixels[min(i_pix + 1, len(self.pixels) - 1)]
        l0 = self.lines[i_lin]
        l1 = self.lines[min(i_lin + 1, len(self.lines) - 1)]

        fx = (pixel - p0) / (p1 - p0) if p1 != p0 else 0
        fy = (line - l0) / (l1 - l0) if l1 != l0 else 0

        corners = {}
        for (p, l), (lat, lon) in self._grid.items():
            if p == p0 and l == l0: corners['tl'] = (lat, lon)
            elif p == p1 and l == l0: corners['tr'] = (lat, lon)
            elif p == p0 and l == l1: corners['bl'] = (lat, lon)
            elif p == p1 and l == l1: corners['br'] = (lat, lon)

        if len(corners) < 4:
            return None, None

        lat = (corners['tl'][0] * (1 - fx) * (1 - fy) +
               corners['tr'][0] * fx * (1 - fy) +
               corners['bl'][0] * (1 - fx) * fy +
               corners['br'][0] * fx * fy)
        lon = (corners['tl'][1] * (1 - fx) * (1 - fy) +
               corners['tr'][1] * fx * (1 - fy) +
               corners['bl'][1] * (1 - fx) * fy +
               corners['br'][1] * fx * fy)
        return lat, lon

    def latlon_to_pixel(self, target_lat, target_lon):
        best = None
        best_dist = float('inf')
        for (pix, lin, lat, lon) in self.points:
            d = (lat - target_lat) ** 2 + (lon - target_lon) ** 2
            if d < best_dist:
                best_dist = d
                best = (pix, lin, lat, lon)
        return best


# ============================================================
# CFAR VECTORISÉ
# ============================================================
def cfar_detect(image):
    print("      Filtre médian (scipy)...", flush=True)
    img = median_filter(image.astype(np.float32), size=3)

    print("      Calcul des statistiques locales...", flush=True)
    h, w = img.shape
    g = CFAR_GUARD
    t = CFAR_TRAIN
    size = 2 * (t + g) + 1

    mean_local = uniform_filter(img, size=size, mode='constant')
    sq_mean = uniform_filter(img ** 2, size=size, mode='constant')
    var_local = np.maximum(sq_mean - mean_local ** 2, 0)
    std_local = np.sqrt(var_local)

    print("      Seuillage...", flush=True)
    threshold = mean_local + CFAR_THRESHOLD_FACTOR * std_local
    mask = (img > threshold) & (img > mean_local * MIN_INTENSITY_RATIO)

    mask[:t + g, :] = False
    mask[-(t + g):, :] = False
    mask[:, :t + g] = False
    mask[:, -(t + g):] = False

    print("      Extraction des coordonnées...", flush=True)
    ys, xs = np.where(mask)
    detections = []
    for y, x in zip(ys, xs):
        detections.append({
            'x': int(x),
            'y': int(y),
            'intensity': float(img[y, x]),
            'threshold': float(threshold[y, x]),
            'ratio': float(img[y, x] / max(mean_local[y, x], 1))
        })

    return detections


# ============================================================
# CLUSTERING
# ============================================================
def cluster_detections(detections):
    if not detections:
        return []

    pts = np.array([[d['x'], d['y']] for d in detections])
    intensities = np.array([d['intensity'] for d in detections])

    tree = cKDTree(pts)
    pairs = tree.query_pairs(CLUSTER_RADIUS_PX)

    parent = list(range(len(pts)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i, j):
        pi, pj = find(i), find(j)
        if pi != pj:
            parent[pi] = pj

    for i, j in pairs:
        union(i, j)

    groups = {}
    for i in range(len(pts)):
        root = find(i)
        groups.setdefault(root, []).append(i)

    clusters = []
    for indices in groups.values():
        if len(indices) >= MIN_VESSEL_PIXELS:
            cluster_pts = pts[indices]
            cx = float(cluster_pts[:, 0].mean())
            cy = float(cluster_pts[:, 1].mean())
            intensity = float(intensities[indices].max())
            clusters.append({
                'x': cx, 'y': cy,
                'intensity': intensity,
                'pixels': len(indices)
            })

    return clusters


def haversine_m(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ============================================================
# PIPELINE PRINCIPAL
# ============================================================
def main():
    print("=" * 60)
    print("  🌊 Détection SAR — La Réunion (mode sans AIS)")
    print("=" * 60)

    print("\n[1/6] Chargement de la grille de géolocalisation...")
    geo = SarGeolocator(SAFE_DIR, polarization='vv')
    print(f"      {len(geo.points)} points chargés")

    print(f"\n[2/6] Localisation de La Réunion ({REUNION_LAT}, {REUNION_LON})...")
    rp = geo.latlon_to_pixel(REUNION_LAT, REUNION_LON)
    if not rp:
        print("      ❌ Impossible de localiser La Réunion")
        return
    px_reu, py_reu, lat_ref, lon_ref = rp
    print(f"      Pixel Réunion : ({px_reu}, {py_reu})")
    print(f"      Vérif GPS : {lat_ref:.4f}, {lon_ref:.4f}")

    first_line_pts = sorted([p for p in geo.points if p[1] == geo.lines[0]], key=lambda x: x[0])
    lon_span = abs(first_line_pts[-1][3] - first_line_pts[0][3])
    px_span_lon = first_line_pts[-1][0] - first_line_pts[0][0]
    px_per_deg_lon = px_span_lon / lon_span if lon_span > 0 else 1300

    first_col_pts = sorted([p for p in geo.points if p[0] == geo.pixels[0]], key=lambda x: x[1])
    lat_span = abs(first_col_pts[-1][2] - first_col_pts[0][2])
    py_span_lat = first_col_pts[-1][1] - first_col_pts[0][1]
    px_per_deg_lat = py_span_lat / lat_span if lat_span > 0 else 1300

    print(f"      Pixels/degré : lon={px_per_deg_lon:.0f}, lat={px_per_deg_lat:.0f}")

    radius_deg_lat = RADIUS_KM / KM_PER_DEG_LAT
    radius_deg_lon = RADIUS_KM / (KM_PER_DEG_LAT * math.cos(math.radians(REUNION_LAT)))

    half_w = int(radius_deg_lon * px_per_deg_lon)
    half_h = int(radius_deg_lat * px_per_deg_lat)

    tiff = list(SAFE_DIR.glob('measurement/*vv*.tiff'))[0]
    with rasterio.open(tiff) as src:
        img_w, img_h = src.width, src.height

    x0 = max(0, px_reu - half_w)
    y0 = max(0, py_reu - half_h)
    x1 = min(img_w, px_reu + half_w)
    y1 = min(img_h, py_reu + half_h)
    w = x1 - x0
    h = y1 - y0

    print(f"\n[3/6] Fenêtre d'intérêt : x={x0} y={y0} w={w} h={h}")
    print(f"      Soit ~{w*h/1e6:.2f} M pixels ({w}x{h})")

    print(f"\n[4/6] Lecture de {tiff.name}...")
    with rasterio.open(tiff) as src:
        window = Window(x0, y0, w, h)
        img = src.read(1, window=window)
        print(f"      Image lue : {img.shape}  dtype={img.dtype}")

    print(f"\n[5/6] Détection CFAR (seuil={CFAR_THRESHOLD_FACTOR}, ratio={MIN_INTENSITY_RATIO})...")
    raw = cfar_detect(img)
    print(f"      {len(raw)} pixels candidats")
    clusters = cluster_detections(raw)
    print(f"      {len(clusters)} clusters (navires potentiels)")

    # Statistiques de distribution
    if clusters:
        intensities = [c['intensity'] for c in clusters]
        pixels_list = [c['pixels'] for c in clusters]
        print(f"      Distribution intensité : min={min(intensities):.0f} max={max(intensities):.0f} median={np.median(intensities):.0f}")
        print(f"      Distribution pixels   : min={min(pixels_list)} max={max(pixels_list)} median={np.median(pixels_list):.0f}")

    print(f"\n[6/6] Conversion GPS + filtrage côtier...")
    detections = []
    for c in clusters:
        abs_x = x0 + c['x']
        abs_y = y0 + c['y']
        lat, lon = geo.pixel_to_latlon(abs_x, abs_y)
        if lat is None:
            continue
        dist_reu_km = haversine_m(REUNION_LAT, REUNION_LON, lat, lon) / 1000
        if dist_reu_km < MIN_DIST_REU_KM:
            continue
        if dist_reu_km > RADIUS_KM * 1.2:
            continue
        detections.append({
            'lat': lat, 'lon': lon,
            'intensity': c['intensity'],
            'pixels': c['pixels'],
            'dist_reunion_km': dist_reu_km
        })

    print(f"      {len(detections)} détections retenues (au large)")

    ghosts = [
        {
            'lat': d['lat'],
            'lon': d['lon'],
            'intensity': d['intensity'],
            'pixels': d['pixels'],
            'dist_reunion_km': d['dist_reunion_km'],
            'note': 'Détection SAR — vérification visuelle recommandée'
        }
        for d in detections
    ]

    print(f"\n✓ {len(ghosts)} détections SAR à vérifier")

    output = {
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'scene': SAFE_DIR.name,
        'center': {'lat': REUNION_LAT, 'lon': REUNION_LON},
        'radius_km': RADIUS_KM,
        'min_dist_reunion_km': MIN_DIST_REU_KM,
        'mode': 'SAR_only',
        'stats': {
            'total_detections': len(detections),
            'ghosts': len(ghosts)
        },
        'ghosts': ghosts
    }

    with open(OUTPUT_FILE, 'w') as f:
        json.dump(output, f, indent=2)
    print(f"\n✓ Sauvegardé : {OUTPUT_FILE}")


if __name__ == '__main__':
    main()