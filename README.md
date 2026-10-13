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

[Fonctionnalités](#-fonctionnalités) • [Architecture](#-architecture) • [Installation](#-installation) • [Utilisation](#-utilisation) • [Limitations](#-limitations)

</div>

---

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

### Pipeline Ghost Boats

Le pipeline SAR est **manuel** (à cause du temps de traitement et du quota CDSE).

#### Étape 1 — Trouver une scène Sentinel-1

```bash
python3 check_footprints.py
```

Ce script interroge le catalogue CDSE et affiche les scènes qui couvrent **vraiment** La Réunion.

#### Étape 2 — Télécharger la scène

Édite `download_reunion.py` avec l'ID de la scène identifiée, puis :

```bash
python3 download_reunion.py
```

**Durée** : 3-5 minutes (téléchargement ~900 MB).

#### Étape 3 — Détecter les ghost boats

```bash
python3 ghost_pipeline.py
```

**Durée** : 2-3 minutes (CFAR + clustering + croisement GPS).

**Résultat** : `ghost_boats.json` — chargé automatiquement par le serveur au prochain redémarrage.

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
python3 ~/Desktop/NAVY/test_geo.py
```

### Tester le téléchargement CDSE

```bash
python3 test_download.py
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
- [ ] Alertes email

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
