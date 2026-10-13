#!/usr/bin/env python3
"""
Test de téléchargement d'une scène Sentinel-1 depuis CDSE.
Récupère la scène la plus récente et la télécharge dans sar_data/.
"""

import os
import requests
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv('CDSE_CLIENT_ID')
CLIENT_SECRET = os.getenv('CDSE_CLIENT_SECRET')

if not CLIENT_ID or not CLIENT_SECRET:
    print("❌ CDSE_CLIENT_ID et CDSE_CLIENT_SECRET requis dans .env")
    exit(1)

OUTPUT_DIR = Path(__file__).parent / 'sar_data'
OUTPUT_DIR.mkdir(exist_ok=True)

# ============================================================
# 1. AUTHENTIFICATION
# ============================================================
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
print(f"✓ Token obtenu")

# ============================================================
# 2. RECHERCHE DE LA SCÈNE LA PLUS RÉCENTE
# ============================================================
end_date = datetime.utcnow()
start_date = end_date - timedelta(days=30)
polygon = "POLYGON((50 -25, 61 -25, 61 -17, 50 -17, 50 -25))"

print(f"\n→ Recherche Sentinel-1 (30 derniers jours)...")
r = requests.get(
    "https://catalogue.dataspace.copernicus.eu/odata/v1/Products",
    params={
        "$filter": (
            f"Collection/Name eq 'SENTINEL-1' "
            f"and contains(Name,'IW_GRDH') "
            f"and OData.CSC.Intersects(area=geography'SRID=4326;{polygon}') "
            f"and ContentDate/Start ge {start_date.isoformat()}Z"
        ),
        "$select": "Id,Name,ContentDate,ContentLength",
        "$orderby": "ContentDate/Start desc",
        "$top": 1,
    },
    headers={"Authorization": f"Bearer {token}"},
    timeout=60
)
r.raise_for_status()
products = r.json().get("value", [])

if not products:
    print("❌ Aucune scène trouvée")
    exit(1)

product = products[0]
size_gb = product.get('ContentLength', 0) / (1024 ** 3)
print(f"✓ Scène trouvée :")
print(f"  Nom    : {product['Name']}")
print(f"  Date   : {product['ContentDate']['Start']}")
print(f"  Taille : {size_gb:.2f} GB")
print(f"  ID     : {product['Id']}")

# ============================================================
# 3. CONFIRMATION
# ============================================================
print(f"\n⚠️  Le téléchargement va prendre du temps ({size_gb:.2f} GB).")
print(f"⚠️  Destination : {OUTPUT_DIR}")
resp = input("\nContinuer ? (o/N) : ").strip().lower()
if resp != 'o':
    print("Annulé.")
    exit(0)

# ============================================================
# 4. TÉLÉCHARGEMENT
# ============================================================
# Construction de l'URL de téléchargement
product_id = product['Id']
download_url = f"https://download.dataspace.copernicus.eu/odata/v1/Products({product_id})/$value"

output_file = OUTPUT_DIR / f"{product['Name']}.zip"

if output_file.exists():
    print(f"\n✓ Fichier déjà présent : {output_file}")
    print(f"  Taille : {output_file.stat().st_size / (1024**3):.2f} GB")
    exit(0)

print(f"\n→ Téléchargement de {product['Name']}...")
print(f"  URL : {download_url[:80]}...")

# Authentification pour le téléchargement
r = requests.get(
    download_url,
    headers={"Authorization": f"Bearer {token}"},
    stream=True,
    timeout=600,
    allow_redirects=True
)
r.raise_for_status()

total_size = int(r.headers.get('content-length', 0))
print(f"  Taille annoncée : {total_size / (1024**3):.2f} GB")
print(f"  Écriture dans  : {output_file}")

downloaded = 0
chunk_size = 1024 * 1024  # 1 MB
last_print = 0

with open(output_file, 'wb') as f:
    for chunk in r.iter_content(chunk_size=chunk_size):
        if chunk:
            f.write(chunk)
            downloaded += len(chunk)

            # Affiche la progression tous les 100 MB
            if downloaded - last_print > 100 * 1024 * 1024:
                pct = (downloaded / total_size * 100) if total_size > 0 else 0
                print(f"  {downloaded / (1024**3):.2f} / {total_size / (1024**3):.2f} GB  ({pct:.1f}%)")
                last_print = downloaded

print(f"\n✓ Téléchargement terminé")
print(f"  Fichier : {output_file}")
print(f"  Taille  : {output_file.stat().st_size / (1024**3):.2f} GB")

# ============================================================
# 5. APERÇU DU CONTENU
# ============================================================
import zipfile
print(f"\n→ Aperçu du contenu (10 premiers fichiers) :")
with zipfile.ZipFile(output_file, 'r') as z:
    names = z.namelist()
    print(f"  Total : {len(names)} fichiers")
    for name in names[:10]:
        info = z.getinfo(name)
        print(f"  • {name}  ({info.file_size / (1024**2):.1f} MB)")
    if len(names) > 10:
        print(f"  ... et {len(names) - 10} autres")

print("\n✓ Test terminé avec succès")