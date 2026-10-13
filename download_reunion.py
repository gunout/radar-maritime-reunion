#!/usr/bin/env python3
"""
Télécharge la scène Sentinel-1 qui couvre La Réunion.

Lit la scène depuis pending_scene.txt (écrit par auto_update.py).
Si absent, utilise la scène hardcodée (fallback pour test manuel).

Correctifs :
  - Vérifie la taille du .zip existant avant de l'accepter (détecte les téléchargements incomplets)
  - Teste l'intégrité du zip (testzip) avant extraction
  - Supprime les .zip corrompus au lieu de planter
  - Vérifie que le .SAFE extrait contient bien des TIFF
  - Supprime le .zip après extraction réussie (économie disque)
"""

import os
import sys
import shutil
import requests
import zipfile
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
CLIENT_ID = os.getenv('CDSE_CLIENT_ID')
CLIENT_SECRET = os.getenv('CDSE_CLIENT_SECRET')

if not CLIENT_ID or not CLIENT_SECRET:
    print("❌ CDSE_CLIENT_ID et CDSE_CLIENT_SECRET requis dans .env")
    sys.exit(1)

# ============================================================
# SÉLECTION DE LA SCÈNE
# ============================================================
PENDING_FILE = Path(__file__).parent / 'pending_scene.txt'

PRODUCT_ID = None
PRODUCT_NAME = None
EXPECTED_SIZE = None

if PENDING_FILE.exists():
    lines = PENDING_FILE.read_text().strip().split('\n')
    if len(lines) >= 2:
        PRODUCT_ID = lines[0].strip()
        PRODUCT_NAME = lines[1].strip()
        if len(lines) >= 3:
            try:
                EXPECTED_SIZE = int(lines[2].strip())
            except ValueError:
                EXPECTED_SIZE = None
        print(f"→ Scène depuis pending_scene.txt : {PRODUCT_NAME}")
    else:
        print("⚠️  pending_scene.txt mal formé — utilisation fallback")

if not PRODUCT_ID:
    # Fallback : scène hardcodée (8 octobre)
    PRODUCT_ID = '48156e85-1b59-4de9-8569-227446811951'
    PRODUCT_NAME = 'S1D_IW_GRDH_1SDV_20261008T014642_20261008T014707_004917_009431_8659_COG.SAFE'
    print(f"→ Scène hardcodée (fallback) : {PRODUCT_NAME}")

print(f"   ID : {PRODUCT_ID}")

OUTPUT_DIR = Path(__file__).parent / 'sar_data'
OUTPUT_DIR.mkdir(exist_ok=True)

output_file = OUTPUT_DIR / f"{PRODUCT_NAME}.zip"
safe_dir = OUTPUT_DIR / PRODUCT_NAME

# ============================================================
# AUTHENTIFICATION
# ============================================================
print("\n→ Authentification CDSE...")
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

# ============================================================
# VÉRIFICATION DU .SAFE DÉJÀ EXTRAIT
# ============================================================
if safe_dir.exists() and safe_dir.is_dir():
    measurement_dir = safe_dir / 'measurement'
    tiffs = list(measurement_dir.glob('*.tiff')) if measurement_dir.exists() else []
    if tiffs:
        print(f"✓ Scène déjà extraite : {safe_dir}")
        print(f"   {len(tiffs)} fichier(s) TIFF présent(s)")
        print("   → Rien à faire")
        sys.exit(0)
    else:
        print(f"⚠️  Dossier .SAFE incomplet, suppression : {safe_dir.name}")
        shutil.rmtree(safe_dir)

# ============================================================
# VÉRIFICATION DU .ZIP EXISTANT
# ============================================================
need_download = True

if output_file.exists():
    actual_size = output_file.stat().st_size
    print(f"\n→ Fichier zip existant : {actual_size / 1e6:.0f} Mo")

    # Vérification 1 : taille attendue (si connue)
    size_ok = True
    if EXPECTED_SIZE:
        threshold = EXPECTED_SIZE * 0.98
        if actual_size < threshold:
            print(f"⚠️  Taille insuffisante ({actual_size} < {EXPECTED_SIZE} attendus)")
            size_ok = False

    # Vérification 2 : test d'intégrité du zip
    integrity_ok = False
    if size_ok:
        try:
            with zipfile.ZipFile(output_file, 'r') as z:
                bad = z.testzip()
                if bad is None:
                    integrity_ok = True
                else:
                    print(f"⚠️  Zip corrompu (fichier défectueux : {bad})")
        except zipfile.BadZipFile:
            print(f"⚠️  Zip corrompu (BadZipFile)")

    if size_ok and integrity_ok:
        print(f"✓ Zip valide et complet")
        need_download = False
    else:
        print(f"   → Suppression et re-téléchargement")
        output_file.unlink()

# ============================================================
# TÉLÉCHARGEMENT
# ============================================================
if need_download:
    download_url = f"https://download.dataspace.copernicus.eu/odata/v1/Products({PRODUCT_ID})/$value"

    print(f"\n→ Téléchargement de {PRODUCT_NAME}...")
    print(f"   URL : {download_url}")

    r = requests.get(
        download_url,
        headers={"Authorization": f"Bearer {token}"},
        stream=True,
        timeout=(30, 120),  # connect timeout 30s, read timeout 120s
        allow_redirects=True
    )
    r.raise_for_status()

    total_size = int(r.headers.get('content-length', 0))
    if total_size == 0:
        total_size = EXPECTED_SIZE or 0

    if total_size:
        print(f"   Taille annoncée : {total_size / 1e6:.0f} Mo")

    downloaded = 0
    last_print = 0

    try:
        with open(output_file, 'wb') as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if downloaded - last_print > 50 * 1024 * 1024:
                        pct = (downloaded / total_size * 100) if total_size > 0 else 0
                        print(f"  {downloaded / 1e6:.0f} / {total_size / 1e6:.0f} Mo  ({pct:.1f}%)", flush=True)
                        last_print = downloaded
    except (requests.exceptions.ChunkedEncodingError,
            requests.exceptions.ConnectionError) as e:
        print(f"\n❌ Téléchargement interrompu : {e}")
        print(f"   Fichier partiel : {output_file} ({downloaded / 1e6:.0f} Mo)")
        print(f"   Relancez le script pour reprendre (le zip partiel sera supprimé)")
        sys.exit(1)

    final_size = output_file.stat().st_size
    print(f"\n✓ Téléchargement terminé : {final_size / 1e6:.0f} Mo")

    # Vérification post-téléchargement
    if total_size > 0 and final_size < total_size * 0.98:
        print(f"❌ Fichier incomplet ({final_size} < {total_size})")
        print(f"   Suppression et relance recommandée")
        output_file.unlink()
        sys.exit(1)

# ============================================================
# EXTRACTION
# ============================================================
print(f"\n→ Extraction de {output_file.name}...")

try:
    with zipfile.ZipFile(output_file, 'r') as z:
        bad = z.testzip()
        if bad:
            print(f"❌ Zip corrompu — fichier défectueux : {bad}")
            output_file.unlink()
            sys.exit(1)
        z.extractall(OUTPUT_DIR)
    print(f"✓ Extrait dans {OUTPUT_DIR}")
except zipfile.BadZipFile as e:
    print(f"❌ BadZipFile : {e}")
    print(f"   Suppression du zip corrompu")
    output_file.unlink()
    sys.exit(1)

# ============================================================
# VÉRIFICATION POST-EXTRACTION
# ============================================================
measurement_dir = safe_dir / 'measurement'
if not measurement_dir.exists():
    print(f"❌ Dossier 'measurement' introuvable dans {safe_dir}")
    sys.exit(1)

tiffs = list(measurement_dir.glob('*.tiff'))
if not tiffs:
    print(f"❌ Aucun fichier TIFF dans {measurement_dir}")
    sys.exit(1)

print(f"✓ {len(tiffs)} fichier(s) TIFF extrait(s)")

# ============================================================
# NETTOYAGE
# ============================================================
if output_file.exists():
    output_file.unlink()
    print(f"✓ Zip supprimé (économie disque)")

print(f"\n✓ Terminé — Scène prête : {safe_dir.name}")
