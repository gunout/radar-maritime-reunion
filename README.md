<div align="center">

# 🌊 Radar Maritime Réunion

**Veille maritime open source autour de La Réunion**

Détection de navires par imagerie satellite SAR • Séismes temps réel • Cartographie interactive

[![Made with Node.js](https://img.shields.io/badge/Node.js-18%2B-339933?logo=node.js&logoColor=white)](https://nodejs.org)
[![Made with Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://python.org)
[![Sentinel-1](https://img.shields.io/badge/Sentinel--1-Copernicus-003399?logo=esa&logoColor=white)](https://dataspace.copernicus.eu)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![GitHub stars](https://img.shields.io/github/stars/gunout/radar-maritime-reunion?style=social)](https://github.com/gunout/radar-maritime-reunion/stargazers)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](http://makeapullrequest.com)

[Fonctionnalités](#-fonctionnalités) • [Architecture](#-architecture) • [Installation](#-installation) • [Utilisation](#-utilisation) • [Automatisation](#-automatisation-cron) • [Limitations](#️-limitations)

</div>

---
## SCREENSHOTS

<img width="1653" height="2507" alt="Screenshot 2026-10-13 at 23-51-45 Radar Maritime Réunion — Surveillance open source" src="https://github.com/user-attachments/assets/6a799f6a-3b34-4ee3-97b3-a41758d0f772" />


## 📖 À propos

**Radar Maritime Réunion** est un outil de veille maritime **open source** qui combine plusieurs sources de données publiques pour surveiller l'activité maritime autour de La Réunion (océan Indien).

Il détecte notamment les **« ghost boats »** — des navires qui naviguent sans émettre leur signal AIS — grâce à l'analyse d'images radar satellitaires Sentinel-1.

> ⚠️ **Outil tiers indépendant.** Ce projet n'est ni édité, ni approuvé, ni affilié à l'Union européenne, à l'État français ou à la Marine Nationale.

---

## ✨ Fonctionnalités

### 🛰️ Détection SAR (Ghost Boats)
- Téléchargement automatique de scènes **Sentinel-1 GRD** depuis Copernicus
- Algorithme **CFAR** (Constant False Alarm Rate) pour détecter les signatures radar
- Clustering spatial avec `scipy.spatial.cKDTree`
- Filtrage géographique (rayon autour de La Réunion)
- Conversion pixel → GPS via grille de géolocalisation

### 🌊 Navires AIS
- Flux temps réel via **AISStream** (WebSocket)
- Filtrage géographique côté serveur
- Affichage sur carte et radar
- ⚠️ Couverture limitée dans l'océan Indien

### 🌍 Séismes
- Flux **USGS** temps réel (M ≥ 2.5, dernières 24 h)
- Affichage carte + tableau + graphiques

### 🗺️ Visualisation
- **Radar circulaire** avec balayage animé
- **Carte interactive** (Leaflet + OpenStreetMap)
- **Tableaux triables** (ghosts, navires, séismes)
- **Exports** CSV et PDF
- **Filtres géographiques** (rectangle dessinable)

### ⏰ Automatisation
- **Cron job** qui vérifie toutes les 30 min les nouvelles scènes Sentinel-1
- Téléchargement et traitement automatiques
- Rechargement à chaud du serveur Node.js
- Nettoyage automatique des vieilles scènes

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    NAVIGATEUR (index.html)              │
│                                                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────┐ │
│  │  Radar   │  │  Carte   │  │ Tableaux │  │ Charts │ │
│  │ circulaire│  │ Leaflet  │  │  triables│  │Chart.js│ │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └───┬────┘ │
│       └─────────────┴─────────────┴────────────┘      │
│                          │                              │
│                    WebSocket (ws://)                    │
└──────────────────────────┼──────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────┐
│              SERVEUR NODE.JS (server.js)                │
│                                                          │
│  ┌─────────────────┐  ┌──────────────┐  ┌────────────┐ │
│  │ HTTP statique   │  │ WebSocket    │  │ ghost_boats│ │
│  │ (index.html)    │  │ relay        │  │ .json      │ │
│  └─────────────────┘  └──────┬───────┘  └────────────┘ │
└──────────────────────────────┼──────────────────────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
              ▼                ▼                ▼
      ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
      │  AISStream   │  │    USGS      │  │  Pipeline    │
      │  (WebSocket) │  │  (HTTPS)     │  │  Python SAR  │
      └──────────────┘  └──────────────┘  └──────┬───────┘
                                                  │
                                                  ▼
                                          ┌──────────────┐
                                          │ Copernicus   │
                                          │ Sentinel-1   │
                                          └──────────────┘
                                                  ▲
                                                  │
                                          ┌──────────────┐
                                          │  CRON JOB    │
                                          │  (30 min)    │
                                          └──────────────┘
```

---

## 🚀 Installation

### Prérequis

| Outil | Version | Utilité |
|---|---|---|
| **Node.js** | 18+ | Serveur HTTP + WebSocket |
| **Python** | 3.10+ | Pipeline SAR (CFAR) |
| **Compte CDSE** | gratuit | Téléchargement Sentinel-1 |
| **Compte AISStream** | gratuit | Flux AIS temps réel |

### 1. Cloner le repository

```bash
git clone https://github.com/gunout/radar-maritime-reunion.git
cd radar-maritime-reunion
```

### 2. Installer les dépendances Node.js

```bash
npm install
```

### 3. Installer les dépendances Python

```bash
pip install numpy rasterio scikit-image scipy requests python-dotenv
```

### 4. Créer le fichier `.env`

```bash
cp .env.example .env
nano .env
```

Remplir avec tes clés :

```env
# AISStream (https://aisstream.io/account)
AISSTREAM_API_KEY=ta_clé_aisstream

# Copernicus Data Space (https://dataspace.copernicus.eu)
CDSE_CLIENT_ID=ton_client_id
CDSE_CLIENT_SECRET=ton_client_secret
```

> 🔑 **Comment obtenir les clés ?**
>
> **AISStream** : crée un compte sur [aisstream.io](https://aisstream.io), puis va dans `Account` → `Create API key`.
>
> **Copernicus** : crée un compte sur [dataspace.copernicus.eu](https://dataspace.copernicus.eu), puis dans le Dashboard → `Sentinel Hub` → `OAuth clients` → `Create new OAuth client`.

### 5. Lancer le serveur

```bash
node server.js
```

Ouvrir **[http://localhost:9013](http://localhost:9013)** dans ton navigateur.

---

## 🎯 Utilisation

### Lancer le serveur

```bash
node server.js
```

Le serveur :
- Sert `index.html` sur `http://localhost:9013`
- Ouvre un WebSocket sur `ws://localhost:9013/ws`
- Se connecte à AISStream
- Charge `ghost_boats.json` au démarrage

### Pipeline Ghost Boats manuel

#### Étape 1 — Trouver une scène Sentinel-1

```bash
python3 check_footprints.py
```

#### Étape 2 — Télécharger la scène

```bash
python3 download_reunion.py
```

**Durée** : 3-5 minutes (téléchargement ~900 MB).

#### Étape 3 — Détecter les ghost boats

```bash
python3 ghost_pipeline.py
```

**Durée** : 2-3 minutes (CFAR + clustering + croisement GPS).

**Résultat** : `ghost_boats.json` — chargé automatiquement par le serveur.

---

## ⏰ Automatisation (CRON)

Le radar peut fonctionner **entièrement automatiquement** grâce à un cron job qui vérifie les nouvelles scènes Sentinel-1 toutes les 30 minutes.

### 📋 Vue d'ensemble

| Fréquence | Tâche | Fichier de log |
|-----------|-------|----------------|
| **Toutes les 30 min** | Vérifier nouvelle scène + pipeline SAR | `logs/cron.log` |
| **Tous les jours à 3h** | Nettoyer les scènes > 30 jours | `logs/cleanup.log` |
| **Toutes les heures** | Vérifier que le serveur Node tourne | `logs/server.log` |

### 🔧 Étape 1 — Créer `auto_update.py`

Ce script vérifie s'il y a une **nouvelle** scène Sentinel-1 disponible sur le CDSE, et si oui, la télécharge et lance le pipeline CFAR.

Le fichier est déjà présent dans le repo : [`auto_update.py`](./auto_update.py).

### 🔧 Étape 2 — Créer le dossier `logs`

```bash
mkdir -p logs
```

### 🔧 Étape 3 — Éditer le crontab

```bash
crontab -e
```

**Ajoutez ces lignes** à la fin du fichier (adaptez `/home/gleaphe/Desktop/NAVY` à votre chemin) :

```cron
# ============================================================
# Environnement cron
# ============================================================
PATH=/usr/local/bin:/usr/bin:/bin
SHELL=/bin/bash
MAILTO=""

# ============================================================
# RADAR MARITIME RÉUNION — Tâches automatiques
# ============================================================

# Toutes les 30 minutes : vérifier nouvelle scène Sentinel-1 + pipeline SAR
*/30 * * * * cd /home/gleaphe/Desktop/NAVY && mkdir -p logs && /usr/bin/python3 auto_update.py >> logs/cron.log 2>&1

# Tous les jours à 3h : nettoyer les vieilles scènes SAR (> 30 jours)
0 3 * * * cd /home/gleaphe/Desktop/NAVY && mkdir -p logs && find sar_data/ -name "*.SAFE" -mtime +30 -exec rm -rf {} \; >> logs/cleanup.log 2>&1

# Toutes les heures : vérifier que le serveur Node tourne, sinon le relancer
0 * * * * pgrep -f "node server.js" > /dev/null || (cd /home/gleaphe/Desktop/NAVY && mkdir -p logs && nohup node server.js >> logs/server.log 2>&1 &)
```

> ⚠️ **Remplacez `/home/gleaphe/Desktop/NAVY` par le chemin absolu de votre projet.**
>
> Pour connaître votre chemin exact :
>
> ```bash
> pwd
> ```
>
> Si vous avez cloné le repo dans votre home, ça sera `/home/votre_user/radar-maritime-reunion`.

**Sauvegarder et quitter** (nano : `Ctrl+O`, `Entrée`, `Ctrl+X`).

### 🔧 Étape 4 — Vérifier l'installation

**Vérifier le crontab** :

```bash
crontab -l | grep radar
```

Vous devez voir les 3 lignes.

**Vérifier que les chemins sont corrects** :

```bash
which python3
which node
```

Adaptez les chemins dans le crontab si nécessaire (par exemple `/usr/local/bin/python3` au lieu de `/usr/bin/python3`).

### 🔧 Étape 5 — Test manuel AVANT de laisser tourner

**C'est crucial.** Si le script a une erreur, le cron va échouer silencieusement.

```bash
cd ~/radar-maritime-reunion
python3 auto_update.py
```

**Cas 1 — Scène déjà traitée** :

```
[2026-10-13 11:30:00] 🔍 Vérification nouvelle scène Sentinel-1...
[2026-10-13 11:30:00]    Dernière scène traitée : S1D_IW_GRDH_1SDV_20261008T...
[2026-10-13 11:30:01] 📡 Scène récente : S1D_IW_GRDH_1SDV_20261008T...
[2026-10-13 11:30:01] ✓ Déjà traitée — rien à faire
```

→ **Le cron peut tourner sans risque.**

**Cas 2 — Nouvelle scène détectée** :

```
[2026-10-13 11:30:00] 🆕 NOUVELLE SCÈNE — Lancement du pipeline...
[2026-10-13 11:30:01]    → Téléchargement de la scène...
...
[2026-10-13 11:35:00]    ✓ Téléchargement OK
[2026-10-13 11:35:00]    → Détection CFAR...
...
[2026-10-13 11:40:00] ✅ Terminé ! Scène traitée : S1D_IW_GRDH_1SDV_20261014T...
```

→ Le pipeline tourne (5-10 minutes).

### 📊 Étape 6 — Surveiller les logs

**En temps réel** :

```bash
tail -f logs/cron.log
```

**Voir les dernières exécutions** :

```bash
cat logs/cron.log
```

**Voir les erreurs** :

```bash
grep -i error logs/cron.log
```

**Preuve côté syslog que cron a lancé la tâche** :

```bash
grep "auto_update" /var/log/syslog | tail -5
```

### 🔍 Étape 7 — Vérifier que le cron tourne

**Attendez 30 minutes** (jusqu'à la prochaine demi-heure pile), puis :

```bash
ls -lh logs/cron.log
cat logs/cron.log
```

Si le fichier contient des logs récents, **le cron fonctionne**.

### 🛑 Désactiver le cron

**Commenter les lignes** dans le crontab :

```bash
crontab -e
# Ajoutez # au début de chaque ligne radar
```

**Ou tout supprimer** :

```bash
crontab -r
```

### ⚠️ Points d'attention

**1. Chemins absolus obligatoires**

Le cron n'utilise **pas** votre `~/.bashrc`, donc :

- Chemins absolus partout (`/usr/bin/python3`, pas `python3`)
- `cd` avant chaque commande
- Variables d'environnement chargées via `dotenv` (pas via le shell)

**2. Le dossier `logs/` doit exister**

Sans le dossier `logs/`, la redirection `>> logs/cron.log` échoue **avant même** de lancer Python. C'est pourquoi le crontab ci-dessus inclut `mkdir -p logs &&` à chaque ligne — comme ça, même si `logs/` est supprimé, cron le recrée automatiquement.

**3. Fréquence et ressources**

Le pipeline SAR utilise **2-3 minutes de CPU** par exécution. Toutes les 30 minutes = charge continue.

**Recommandation** : si votre machine est lente, réduisez à toutes les 6 heures :

```cron
0 */6 * * * cd /home/gleaphe/Desktop/NAVY && mkdir -p logs && /usr/bin/python3 auto_update.py >> logs/cron.log 2>&1
```

Sentinel-1 ne passe que tous les 6 jours, donc toutes les 6 heures est largement suffisant.

**4. Éviter les exécutions en double**

Si le pipeline tourne plus longtemps que l'intervalle, deux instances peuvent se lancer en parallèle. Utilisez `flock` :

```cron
*/30 * * * * flock -n /tmp/radar.lock -c 'cd /home/gleaphe/Desktop/NAVY && mkdir -p logs && /usr/bin/python3 auto_update.py >> logs/cron.log 2>&1'
```

**5. Logs obligatoires**

Sans `>> logs/cron.log 2>&1`, vous ne verrez **aucune erreur**. Toujours rediriger.

**6. Test avant de laisser tourner**

**Testez toujours `python3 auto_update.py` manuellement** avant de compter sur le cron.

### 📋 Récapitulatif du flux automatique

```
Cron (toutes les 30 min)
    ↓
auto_update.py
    ↓
Vérifie CDSE pour nouvelle scène
    ↓
Si nouvelle scène :
    ├── Télécharge (900 MB)
    ├── Lance ghost_pipeline.py (CFAR)
    └── Met à jour ghost_boats.json
    ↓
Serveur Node.js (fs.watch)
    ↓
Recharge automatiquement
    ↓
Navigateur (WebSocket)
    ↓
Affiche les nouvelles détections
```

**Vous n'avez plus rien à faire.** Le radar se met à jour tout seul à chaque nouvelle scène Sentinel-1.

---

## ⚠️ Limitations

### Sentinel-1 — passages bi-hebdomadaires

Les satellites Sentinel-1A et Sentinel-1C passent au-dessus de La Réunion **tous les 6 jours**. Il n'y a donc **pas de mise à jour temps réel** des ghost boats — seulement des **snapshots** réguliers.

### AISStream — couverture limitée

AISStream agrège des récepteurs **bénévoles** (VHF). Dans l'océan Indien sud, ces récepteurs sont **quasi absents**. Les seuls navires reçus proviennent de **Durban** (Afrique du Sud, à 2300 km).

**Conséquence** : le croisement SAR ↔ AIS est impossible pour La Réunion. Toutes les détections SAR sont donc considérées comme des « ghost boats » potentiels (à vérifier visuellement).

### Ghost boats — vérification manuelle

Une détection SAR peut être :
- Un **vrai navire** ✅
- Un **artefact côtier** (falaise, ville) ❌
- Un **phénomène naturel** (vague, écume, baleine) ❌
- Un **débris flottant** ❌

Une **vérification visuelle** sur l'image SAR originale est recommandée pour chaque détection.

---

## 🧪 Tests

### Tester la connexion AISStream

```bash
node ais-relay/test-ais.js
```

### Tester la géolocalisation SAR

```bash
cd sar_data/S1X_..._COG.SAFE
python3 test_geo.py
```

### Tester le téléchargement CDSE

```bash
python3 test_download.py
```

### Tester l'automatisation

```bash
python3 auto_update.py
```

---

## 📦 Stack technique

| Composant | Technologie |
|---|---|
| **Frontend** | HTML5, CSS3, JavaScript vanilla |
| **Carte** | Leaflet 1.9 |
| **Graphiques** | Chart.js 4.4 |
| **Exports** | jsPDF + jsPDF-AutoTable |
| **Serveur** | Node.js 18+, `ws` |
| **Pipeline SAR** | Python 3.10+, NumPy, Rasterio, SciPy, scikit-image |
| **SAR** | Sentinel-1 GRD (Copernicus) |
| **AIS** | AISStream (WebSocket) |
| **Séismes** | USGS GeoJSON |
| **Automatisation** | Cron + auto_update.py |

---

## 🤝 Contribution

Les contributions sont **bienvenues** ! N'hésite pas à :

1. **Fork** le projet
2. Créer une branche (`git checkout -b feature/ma-fonctionnalite`)
3. Commit tes changements (`git commit -m 'Ajout fonctionnalité X'`)
4. Push (`git push origin feature/ma-fonctionnalite`)
5. Ouvrir une **Pull Request**

### Idées d'améliorations

- [ ] Interface d'annotation manuelle des ghost boats
- [ ] Intégration RADARSAT-2 ou ICEYE (SAR haute fréquence)
- [ ] Support de Sentinel-2 (optique)
- [ ] Détection automatique de dark vessels via ML
- [ ] Export GeoJSON
- [ ] Alertes email / Telegram
- [ ] Dashboard web pour surveiller le cron

---

## 📄 Licence

Ce projet est sous licence **MIT** — voir le fichier [LICENSE](LICENSE) pour plus de détails.

---

## 🙏 Remerciements

- [**Copernicus Data Space**](https://dataspace.copernicus.eu) — données Sentinel-1 SAR
- [**AISStream**](https://aisstream.io) — flux AIS temps réel
- [**USGS**](https://earthquake.usgs.gov) — données sismiques
- [**OpenStreetMap**](https://openstreetmap.org) — fond de carte
- [**Leaflet**](https://leafletjs.com) — bibliothèque cartographique

---

## ⚖️ Avertissement

Cet outil est fourni **à titre informatif uniquement**. Les détections SAR sont **automatiques** et peuvent contenir des **faux positifs**. Aucune décision opérationnelle ne doit être prise sur la seule base de ces données.

L'auteur décline toute responsabilité quant à l'usage qui pourrait être fait de cet outil.

---

<div align="center">

**Fait avec ❤️ à La Réunion 🇷🇪**

[⬆ Retour en haut](#-radar-maritime-réunion)

</div>

---

<div align="center">

### 🇫🇷 Gunout · 2026

![Made in France](https://img.shields.io/badge/Made_in-France-002395?style=flat-square&labelColor=FFFFFF&logo=data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCA5MDAgNjAwIj48cmVjdCB3aWR0aD0iOTAwIiBoZWlnaHQ9IjYwMCIgZmlsbD0iIzAwMjM5NSIvPjxyZWN0IHdpZHRoPSI5MDAiIGhlaWdodD0iNDAwIiB5PSIxMDAiIGZpbGw9IiNmZmYiLz48cmVjdCB3aWR0aD0iOTAwIiBoZWlnaHQ9IjIwMCIgeT0iNDAwIiBmaWxsPSIjZWQyOTM5Ii8+PC9zdmc+)
![GitHub](https://img.shields.io/badge/GitHub-gunout-181717?style=flat-square&logo=github&logoColor=white)
![Year](https://img.shields.io/badge/2026-ED2939?style=flat-square&labelColor=FFFFFF)

<sub>© 2026 <strong>Gunout</strong> — Tous droits réservés.</sub>

</div>
