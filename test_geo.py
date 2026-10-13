#!/usr/bin/env python3
"""Extrait la grille de géolocalisation de l'annotation Sentinel-1."""

import xml.etree.ElementTree as ET
import glob
import sys

# Pattern élargi : s1c ou s1d, avec ou sans -cog
ann_files = glob.glob('annotation/s1*-iw-grd-vv-*.xml')
if not ann_files:
    print("❌ Fichier annotation VV introuvable")
    print("Fichiers disponibles :")
    for f in glob.glob('annotation/*.xml'):
        print(f"  {f}")
    sys.exit(1)

ann_file = ann_files[0]
print(f"Annotation : {ann_file}")

tree = ET.parse(ann_file)
root = tree.getroot()
print(f"Tag racine : {root.tag}")

points = []
for pt in root.iter('geolocationGridPoint'):
    line = int(pt.find('line').text)
    pixel = int(pt.find('pixel').text)
    lat = float(pt.find('latitude').text)
    lon = float(pt.find('longitude').text)
    points.append((pixel, line, lat, lon))

print(f"\n{len(points)} points de géolocalisation extraits")

if not points:
    print("\n⚠️  Aucun point trouvé.")
    sys.exit(1)

print(f"\nPremiers points :")
for p in points[:5]:
    print(f"  pixel={p[0]:6d}  line={p[1]:6d}  lat={p[2]:+.4f}  lon={p[3]:+.4f}")

print(f"\nDerniers points :")
for p in points[-5:]:
    print(f"  pixel={p[0]:6d}  line={p[1]:6d}  lat={p[2]:+.4f}  lon={p[3]:+.4f}")

lats = [p[2] for p in points]
lons = [p[3] for p in points]
print(f"\nEmprise GPS :")
print(f"  Lat : {min(lats):.3f} à {max(lats):.3f}")
print(f"  Lon : {min(lons):.3f} à {max(lons):.3f}")

reunion_lat, reunion_lon = -21.12, 55.53
in_lat = min(lats) <= reunion_lat <= max(lats)
in_lon = min(lons) <= reunion_lon <= max(lons)
print(f"\nLa Réunion est dans la scène : {'✅ OUI' if (in_lat and in_lon) else '❌ NON'}")

lines_unique = sorted(set(p[1] for p in points))
pixels_unique = sorted(set(p[0] for p in points))
print(f"\nGrille : {len(lines_unique)} lignes × {len(pixels_unique)} colonnes")
print(f"  Lignes (line) : {lines_unique[:5]} ... {lines_unique[-3:]}")
print(f"  Colonnes (pixel) : {pixels_unique[:5]} ... {pixels_unique[-3:]}")