#!/usr/bin/env python3
"""Télécharge la scène Sentinel-1 qui couvre La Réunion."""

import os
import requests
import zipfile
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
CLIENT_ID = os.getenv('CDSE_CLIENT_ID')
CLIENT_SECRET = os.getenv('CDSE_CLIENT_SECRET')

# Scène identifiée par check_footprints.py
PRODUCT_ID = '48156e85-1b59-4de9-8569-227446811951'
PRODUCT_NAME = 'S1D_IW_GRDH_1SDV_20261008T014642_20261008T014707_004917_009431_8659_COG.SAFE'

OUTPUT_DIR = Path(__file__).parent / 'sar_data'
OUTPUT_DIR.mkdir(exist_ok=True)

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
print("✓ Token obtenu")

# Téléchargement
download_url = f"https://download.dataspace.copernicus.eu/odata/v1/Products({PRODUCT_ID})/$value"
output_file = OUTPUT_DIR / f"{PRODUCT_NAME}.zip"

if not output_file.exists():
    print(f"\n→ Téléchargement de {PRODUCT_NAME}...")
    r = requests.get(
        download_url,
        headers={"Authorization": f"Bearer {token}"},
        stream=True,
        timeout=600,
        allow_redirects=True
    )
    r.raise_for_status()

    total_size = int(r.headers.get('content-length', 0))
    downloaded = 0
    last_print = 0

    with open(output_file, 'wb') as f:
        for chunk in r.iter_content(chunk_size=1024*1024):
            if chunk:
                f.write(chunk)
                downloaded += len(chunk)
                if downloaded - last_print > 50 * 1024 * 1024:
                    pct = (downloaded / total_size * 100) if total_size > 0 else 0
                    print(f"  {downloaded / (1024**3):.2f} / {total_size / (1024**3):.2f} GB  ({pct:.1f}%)")
                    last_print = downloaded

    print(f"\n✓ Téléchargement terminé : {output_file}")
    print(f"  Taille : {output_file.stat().st_size / (1024**3):.2f} GB")
else:
    print(f"\n✓ Fichier déjà présent : {output_file}")

# Extraction
safe_dir = OUTPUT_DIR / PRODUCT_NAME
if not safe_dir.exists():
    print(f"\n→ Extraction...")
    with zipfile.ZipFile(output_file, 'r') as z:
        z.extractall(OUTPUT_DIR)
    print(f"✓ Extrait dans {safe_dir}")
else:
    print(f"\n✓ Déjà extrait : {safe_dir}")