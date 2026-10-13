#!/usr/bin/env python3
"""Cherche une scène Sentinel-1 qui couvre La Réunion."""

import os
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv('CDSE_CLIENT_ID')
CLIENT_SECRET = os.getenv('CDSE_CLIENT_SECRET')

# Auth
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
print("✓ Token obtenu")

# Bbox CENTRÉE sur La Réunion (petite boîte)
polygon = "POLYGON((54.5 -22.0, 56.5 -22.0, 56.5 -20.5, 54.5 -20.5, 54.5 -22.0))"

end_date = datetime.utcnow()
start_date = end_date - timedelta(days=60)

print(f"\n→ Recherche scènes couvrant La Réunion (60 jours)...")
print(f"  Bbox : {polygon}")

r = requests.get(
    "https://catalogue.dataspace.copernicus.eu/odata/v1/Products",
    params={
        "$filter": (
            f"Collection/Name eq 'SENTINEL-1' "
            f"and contains(Name,'IW_GRDH') "
            f"and OData.CSC.Intersects(area=geography'SRID=4326;{polygon}') "
            f"and ContentDate/Start ge {start_date.isoformat()}Z"
        ),
        "$select": "Id,Name,ContentDate,ContentLength,Footprint",
        "$orderby": "ContentDate/Start desc",
        "$top": 20,
    },
    headers={"Authorization": f"Bearer {token}"},
    timeout=60
)
r.raise_for_status()
products = r.json().get("value", [])

print(f"\n✓ {len(products)} scènes trouvées\n")

# Affiche et filtre celles qui couvrent vraiment La Réunion
REUNION_LAT, REUNION_LON = -21.12, 55.53

valid = []
for i, p in enumerate(products, 1):
    name = p['Name']
    footprint = p.get('Footprint', '')
    size_mb = p.get('ContentLength', 0) / (1024*1024)

    # Vérifie que La Réunion est dans le footprint
    if str(REUNION_LON) in footprint or '55.' in footprint or '56.' in footprint:
        # Heuristique : cherche 55.x ou 54.x dans le footprint
        covers = any(f'{lon:.0f}' in footprint for lon in [54, 55, 56])
        marker = '✅' if covers else '❓'
        if covers:
            valid.append(p)
    else:
        marker = ' '

    date = p['ContentDate']['Start'][:19]
    print(f"  {marker} [{i:2d}] {name}")
    print(f"      Date : {date}  |  Taille : {size_mb:.0f} MB")

print(f"\n{'='*60}")
print(f"Scènes valides (couvrent La Réunion) : {len(valid)}")
if valid:
    print(f"\nProchaine scène à télécharger :")
    print(f"  Nom    : {valid[0]['Name']}")
    print(f"  Date   : {valid[0]['ContentDate']['Start']}")
    print(f"  ID     : {valid[0]['Id']}")
