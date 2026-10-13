#!/usr/bin/env python3
"""
Auto-update du radar maritime Réunion.
Vérifie s'il y a une nouvelle scène Sentinel-1 qui couvre La Réunion.
Si oui, télécharge et lance le pipeline ghost boats automatiquement.

Notifications supportées (optionnelles, activables via .env) :
  - Telegram  : TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID
  - Discord   : DISCORD_WEBHOOK_URL
  - Mail      : MAIL_TO (+ commande `mail` disponible)
"""

import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime, timezone, timedelta

import requests
from dotenv import load_dotenv

load_dotenv()

NAVY_DIR = Path(__file__).parent
STATE_FILE = NAVY_DIR / 'last_scene.txt'
PENDING_FILE = NAVY_DIR / 'pending_scene.txt'
LOG_PREFIX = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]"

CLIENT_ID = os.getenv('CDSE_CLIENT_ID')
CLIENT_SECRET = os.getenv('CDSE_CLIENT_SECRET')

# --- Notifications (optionnel) ---
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID   = os.getenv('TELEGRAM_CHAT_ID')
DISCORD_WEBHOOK_URL = os.getenv('DISCORD_WEBHOOK_URL')
MAIL_TO            = os.getenv('MAIL_TO')

REU_LAT = -21.12
REU_LON = 55.53

if not CLIENT_ID or not CLIENT_SECRET:
    print(f"{LOG_PREFIX} ❌ CDSE_CLIENT_ID/SECRET manquants dans .env")
    sys.exit(1)


def log(msg):
    print(f"{LOG_PREFIX} {msg}", flush=True)


# ---------- Notifications ----------

def notify_telegram(message: str):
    if not (TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID):
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            data={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": message,
                "parse_mode": "Markdown",
                "disable_web_page_preview": True,
            },
            timeout=15,
        )
    except Exception as e:
        log(f"⚠️  Telegram échec : {e}")


def notify_discord(message: str):
    if not DISCORD_WEBHOOK_URL:
        return
    try:
        requests.post(
            DISCORD_WEBHOOK_URL,
            json={"content": message[:1900]},
            timeout=15,
        )
    except Exception as e:
        log(f"⚠️  Discord échec : {e}")


def notify_mail(subject: str, message: str):
    if not MAIL_TO:
        return
    try:
        subprocess.run(
            ['mail', '-s', subject, MAIL_TO],
            input=message,
            text=True,
            timeout=15,
        )
    except Exception as e:
        log(f"⚠️  Mail échec : {e}")


def notify_all(message: str, subject: str = "Monitor DAC"):
    log("   → Envoi notifications...")
    notify_telegram(message)
    notify_discord(message)
    notify_mail(subject, message)


# ---------- Code existant ----------

def get_token():
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
    return r.json()["access_token"]


def extract_points(obj):
    pts = []
    if isinstance(obj, (list, tuple)):
        if len(obj) >= 2 and isinstance(obj[0], (int, float)) and isinstance(obj[1], (int, float)):
            pts.append((float(obj[0]), float(obj[1])))
        else:
            for item in obj:
                pts.extend(extract_points(item))
    return pts


def point_in_polygon(lon, lat, poly):
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


def find_latest_scene():
    """Cherche la scène Sentinel-1 la plus récente qui couvre La Réunion."""
    token = get_token()

    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=15)

    polygon = "POLYGON((54.0 -22.5, 57.0 -22.5, 57.0 -20.0, 54.0 -20.0, 54.0 -22.5))"

    r = requests.get(
        "https://catalogue.dataspace.copernicus.eu/odata/v1/Products",
        params={
            "$filter": (
                f"Collection/Name eq 'SENTINEL-1' "
                # ✅ Accepter IW (S1A/S1D) ET S6 (S1C)
                f"and (contains(Name,'IW_GRDH') or contains(Name,'S6_GRDH')) "
                f"and OData.CSC.Intersects(area=geography'SRID=4326;{polygon}') "
                f"and ContentDate/Start ge {start_date.strftime('%Y-%m-%dT%H:%M:%S.000Z')}"
            ),
            "$select": "Id,Name,ContentDate,ContentLength,GeoFootprint",
            "$orderby": "ContentDate/Start desc",
            "$top": 20,
        },
        headers={"Authorization": f"Bearer {token}"},
        timeout=60
    )
    r.raise_for_status()
    products = r.json().get("value", [])

    for p in products:
        gf = p.get('GeoFootprint')
        if not gf or 'coordinates' not in gf:
            continue
        poly = extract_points(gf['coordinates'])
        if poly and point_in_polygon(REU_LON, REU_LAT, poly):
            return p

    return None


def main():
    log("🔍 Vérification nouvelle scène Sentinel-1...")

    last_scene = None
    if STATE_FILE.exists():
        last_scene = STATE_FILE.read_text().strip()
        log(f"   Dernière scène traitée : {last_scene}")

    try:
        scene = find_latest_scene()
    except Exception as e:
        log(f"❌ Erreur recherche: {e}")
        notify_all(f"❌ *Radar Réunion* — erreur recherche scène :\n`{e}`")
        return

    if not scene:
        log("⚠️  Aucune scène trouvée dans les 15 derniers jours")
        return

    scene_name = scene['Name']
    scene_id = scene['Id']
    scene_date = scene['ContentDate']['Start']
    size_mb = scene.get('ContentLength', 0) / (1024 * 1024)

    log(f"📡 Scène récente : {scene_name}")
    log(f"   Date : {scene_date}")
    log(f"   Taille : {size_mb:.0f} MB")

    if last_scene == scene_name:
        log("✓ Déjà traitée — rien à faire")
        return

    log("🆕 NOUVELLE SCÈNE — Lancement du pipeline...")

    notify_all(
        f"🆕 *Radar Réunion* — nouvelle scène détectée\n"
        f"`{scene_name}`\n"
        f"Date : {scene_date}\n"
        f"Taille : {size_mb:.0f} MB\n"
        f"Pipeline en cours...",
        subject="[Radar Réunion] Nouvelle scène Sentinel-1"
    )

    PENDING_FILE.write_text(f"{scene_id}\n{scene_name}")
    log(f"   ✓ pending_scene.txt écrit")

    # Étape 1 : Téléchargement
    log("   → Téléchargement de la scène...")
    try:
        result = subprocess.run(
            ['/usr/bin/python3', str(NAVY_DIR / 'download_reunion.py')],
            cwd=NAVY_DIR,
            capture_output=True,
            text=True,
            timeout=1200
        )
        if result.returncode != 0:
            log(f"❌ Échec téléchargement (code {result.returncode})")
            log(f"   stderr: {result.stderr[-500:]}")
            notify_all(
                f"❌ *Radar Réunion* — échec téléchargement\n"
                f"`{scene_name}`\n"
                f"Code : {result.returncode}\n"
                f"```\n{result.stderr[-500:]}\n```"
            )
            return
        log("   ✓ Téléchargement OK")
    except subprocess.TimeoutExpired:
        log("❌ Timeout téléchargement (>20 min)")
        notify_all(f"❌ *Radar Réunion* — timeout téléchargement\n`{scene_name}`")
        return

    # Étape 2 : Pipeline ghost boats
    log("   → Détection CFAR...")

    # ✅ Trouver le dossier .SAFE le plus récent dans sar_data/
    safe_dirs = sorted(
        (NAVY_DIR / 'sar_data').glob('*.SAFE'),
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )
    if not safe_dirs:
        log("❌ Aucun dossier .SAFE dans sar_data/")
        notify_all("❌ *Radar Réunion* — pas de .SAFE après téléchargement")
        return

    safe_path = safe_dirs[0]
    log(f"   → Traitement de : {safe_path.name}")

    try:
        result = subprocess.run(
            ['/usr/bin/python3', str(NAVY_DIR / 'ghost_pipeline.py'), str(safe_path)],
            cwd=NAVY_DIR,
            capture_output=True,
            text=True,
            timeout=2400
        )
        if result.returncode != 0:
            log(f"❌ Échec pipeline (code {result.returncode})")
            log(f"   stderr: {result.stderr[-500:]}")
            notify_all(
                f"❌ *Radar Réunion* — échec pipeline\n"
                f"`{scene_name}`\n"
                f"Code : {result.returncode}\n"
                f"```\n{result.stderr[-500:]}\n```"
            )
            return
        log("   ✓ Pipeline OK")
    except subprocess.TimeoutExpired:
        log("❌ Timeout pipeline (>40 min)")
        notify_all(f"❌ *Radar Réunion* — timeout pipeline\n`{scene_name}`")
        return

    STATE_FILE.write_text(scene_name)
    log(f"✅ Terminé ! Scène traitée : {scene_name}")

    notify_all(
        f"✅ *Radar Réunion* — pipeline terminé\n"
        f"Scène : `{scene_name}`\n"
        f"Date scène : {scene_date}\n"
        f"Les ghost boats sont à jour.",
        subject="[Radar Réunion] Pipeline terminé"
    )

    if PENDING_FILE.exists():
        PENDING_FILE.unlink()


if __name__ == '__main__':
    main()
