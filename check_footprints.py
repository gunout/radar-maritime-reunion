#!/usr/bin/env python3
"""Test point-in-polygon sur les footprints Sentinel-1 pour trouver la bonne scène."""

import os
import requests
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

load_dotenv()
CLIENT_ID = os.getenv('CDSE_CLIENT_ID')
CLIENT_SECRET = os.getenv('CDSE_CLIENT_SECRET')

# Auth
print("→ Authentification CDSE...")
r = requests.post(
    "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token",
    data={
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    },
    timeout=30
)
r.raise_for_status()
token = r.json()["access_token"]
print("✓ Token obtenu\n")

# Recherche
polygon = "POLYGON((54.0 -22.5, 57.0 -22.5, 57.0 -20.0, 54.0 -20.0, 54.0 -22.5))"
end_date = datetime.now(timezone.utc)
start_date = end_date - timedelta(days=60)

# Format date CDSE : YYYY-MM-DDTHH:MM:SS.000Z
start_str = start_date.strftime('%Y-%m-%dT%H:%M:%S.000Z')

print(f"→ Recherche Sentinel-1 sur 60 jours (54-57°E, -22.5 à -20°S)...")
r = requests.get(
    "https://catalogue.dataspace.copernicus.eu/odata/v1/Products",
    params={
        "$filter": (
            f"Collection/Name eq 'SENTINEL-1' "
            f"and contains(Name,'IW_GRDH') "
            f"and OData.CSC.Intersects(area=geography'SRID=4326;{polygon}') "
            f"and ContentDate/Start ge {start_str}"
        ),
        "$select": "Id,Name,ContentDate,ContentLength,GeoFootprint",
        "$orderby": "ContentDate/Start desc",
        "$top": 30,
    },
    headers={"Authorization": f"Bearer {token}"},
    timeout=60
)

if not r.ok:
    print(f"❌ Erreur HTTP {r.status_code}")
    print(r.text[:500])
    raise SystemExit(1)

products = r.json().get("value", [])
print(f"✓ {len(products)} scènes trouvées\n")


REUNION_LAT, REUNION_LON = -21.12, 55.53


def extract_points(obj):
    """Extrait récursivement toutes les paires (lon, lat) d'une structure GeoJSON."""
    points = []
    if isinstance(obj, (list, tuple)):
        if (len(obj) >= 2
                and isinstance(obj[0], (int, float))
                and isinstance(obj[1], (int, float))):
            points.append((float(obj[0]), float(obj[1])))
        else:
            for item in obj:
                points.extend(extract_points(item))
    return points


def parse_footprint(gf):
    if not gf or 'coordinates' not in gf:
        return None
    return extract_points(gf['coordinates'])


def point_in_polygon(lon, lat, poly):
    """Ray casting."""
    n = len(poly)
    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if ((yi > lat) != (yj > lat)) and (lon < (xj - xi) * (lat - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


valid = []
for i, p in enumerate(products, 1):
    name = p['Name']
    date = p['ContentDate']['Start'][:19]
    size_mb = p.get('ContentLength', 0) / (1024 * 1024)

    poly = parse_footprint(p.get('GeoFootprint'))
    if poly and len(poly) >= 3:
        lons = [c[0] for c in poly]
        lats = [c[1] for c in poly]
        lon_min, lon_max = min(lons), max(lons)
        lat_min, lat_max = min(lats), max(lats)
        covers = point_in_polygon(REUNION_LON, REUNION_LAT, poly)
        marker = '✅' if covers else '  '
        if covers:
            valid.append(p)
    else:
        lon_min = lon_max = lat_min = lat_max = 0
        marker = '?'

    print(f"  {marker} [{i:2d}] {name}")
    print(f"       Date : {date}  |  Taille : {size_mb:.0f} MB")
    print(f"       Lon : {lon_min:.3f} → {lon_max:.3f}  |  Lat : {lat_min:.3f} → {lat_max:.3f}")


print(f"\n{'='*70}")
print(f"Scènes qui couvrent vraiment La Réunion : {len(valid)}")
if valid:
    print(f"\n>>> Meilleure candidate :")
    print(f"  Nom    : {valid[0]['Name']}")
    print(f"  ID     : {valid[0]['Id']}")
    print(f"  Date   : {valid[0]['ContentDate']['Start']}")
    print(f"  Taille : {valid[0].get('ContentLength', 0) / (1024*1024):.0f} MB")