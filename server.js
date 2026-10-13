'use strict';

const http = require('http');
const fs = require('fs');
const path = require('path');
const WebSocket = require('ws');
require('dotenv').config();

const AISSTREAM_KEY = process.env.AISSTREAM_API_KEY;

const PORT = 9013;
const AISSTREAM_URL = 'wss://stream.aisstream.io/v0/stream';
const BOUNDING_BOXES = [[[-50, 20], [10, 100]]];
const FILTER_MESSAGE_TYPES = ['PositionReport', 'ShipStaticData'];

const GHOSTS_FILE = path.join(__dirname, 'ghost_boats.json');

const MIME_TYPES = {
    '.html': 'text/html; charset=utf-8',
    '.js': 'application/javascript; charset=utf-8',
    '.css': 'text/css; charset=utf-8',
    '.json': 'application/json; charset=utf-8',
    '.svg': 'image/svg+xml',
    '.png': 'image/png',
    '.ico': 'image/x-icon'
};

// ============================================================
// SERVEUR HTTP
// ============================================================
const httpServer = http.createServer((req, res) => {
    let filePath = req.url === '/' ? '/index.html' : req.url;
    filePath = filePath.split('?')[0];
    const fullPath = path.join(__dirname, filePath);

    fs.readFile(fullPath, (err, data) => {
        if (err) {
            res.writeHead(404, { 'Content-Type': 'text/plain' });
            res.end('Not found');
            return;
        }
        const ext = path.extname(fullPath).toLowerCase();
        const mime = MIME_TYPES[ext] || 'application/octet-stream';
        res.writeHead(200, { 'Content-Type': mime });
        res.end(data);
    });
});

// ============================================================
// WEBSOCKET
// ============================================================
const wss = new WebSocket.Server({ server: httpServer, path: '/ws' });

// ============================================================
// GHOSTS
// ============================================================
let ghostBoats = [];
let ghostScene = null;
let ghostGeneratedAt = null;

function loadGhostBoats() {
    if (!fs.existsSync(GHOSTS_FILE)) {
        console.log('⚠️  ghost_boats.json absent — 0 ghosts');
        ghostBoats = [];
        ghostScene = null;
        ghostGeneratedAt = null;
        return;
    }
    try {
        const data = JSON.parse(fs.readFileSync(GHOSTS_FILE, 'utf8'));
        ghostBoats = data.ghosts || [];
        ghostScene = data.scene || null;
        ghostGeneratedAt = data.generated_at || null;
        console.log(`👻 ${ghostBoats.length} ghosts chargés`);
        console.log(`   Scène : ${ghostScene || 'inconnue'}`);
        console.log(`   Traitement : ${ghostGeneratedAt || 'inconnu'}`);
    } catch (e) {
        console.log('✗ Erreur lecture ghosts:', e.message);
        ghostBoats = [];
        ghostScene = null;
        ghostGeneratedAt = null;
    }
}

function sendGhostsTo(ws) {
    if (ghostBoats.length > 0) {
        ws.send(JSON.stringify({
            type: 'ghosts',
            count: ghostBoats.length,
            scene: ghostScene,
            generated_at: ghostGeneratedAt,
            ghosts: ghostBoats
        }));
        console.log(`→ ${ghostBoats.length} ghosts envoyés au client (scène ${ghostScene || '?'})`);
    }
}

let ghostWatcher = null;
function watchGhostsFile() {
    if (ghostWatcher) return;
    try {
        ghostWatcher = fs.watch(GHOSTS_FILE, (eventType) => {
            if (eventType === 'change') {
                console.log('🔄 ghost_boats.json modifié — rechargement');
                loadGhostBoats();
                for (const client of wss.clients) {
                    if (client.readyState === WebSocket.OPEN) {
                        sendGhostsTo(client);
                    }
                }
            }
        });
    } catch (e) {
        console.log('⚠️  Impossible de surveiller ghost_boats.json');
    }
}

// ============================================================
// AIS
// ============================================================
let aisSocket = null;
let aisReconnectTimer = null;
let aisReconnectAttempts = 0;
const MAX_RECONNECT_DELAY = 30000;

function connectToAISStream() {
    if (!AISSTREAM_KEY) {
        console.log('⚠️  AISSTREAM_API_KEY manquant — AIS désactivé');
        return;
    }
    if (aisSocket && aisSocket.readyState === WebSocket.OPEN) return;

    console.log('→ Connexion à AISStream...');
    aisSocket = new WebSocket(AISSTREAM_URL);

    aisSocket.on('open', () => {
        console.log('✓ AISStream OPEN — envoi abonnement');
        aisReconnectAttempts = 0;
        aisSocket.send(JSON.stringify({
            APIKey: AISSTREAM_KEY,
            BoundingBoxes: BOUNDING_BOXES,
            FilterMessageTypes: FILTER_MESSAGE_TYPES
        }));
    });

    aisSocket.on('message', (data, isBinary) => {
        const text = isBinary ? data.toString('utf8') : data.toString();
        if (text.includes('SubscriptionConfirmation')) {
            console.log('✓ Abonnement AIS confirmé');
            return;
        }
        if (text.includes('"error"')) {
            console.log('✗ Erreur AISStream:', text.substring(0, 200));
            return;
        }
        broadcast(text);
    });

    aisSocket.on('close', (code) => {
        console.log(`✗ AISStream fermé (code ${code})`);
        aisSocket = null;
        if (wss.clients.size > 0) scheduleReconnect();
    });

    aisSocket.on('error', (err) => {
        console.log('✗ AISStream erreur:', err.message);
    });
}

function broadcast(message) {
    for (const client of wss.clients) {
        if (client.readyState === WebSocket.OPEN) {
            try { client.send(message); } catch (e) {}
        }
    }
}

function scheduleReconnect() {
    if (aisReconnectTimer) return;
    const delay = Math.min(1000 * Math.pow(2, aisReconnectAttempts), MAX_RECONNECT_DELAY);
    aisReconnectAttempts++;
    console.log(`→ Reconnexion AIS dans ${delay}ms`);
    aisReconnectTimer = setTimeout(() => {
        aisReconnectTimer = null;
        connectToAISStream();
    }, delay);
}

wss.on('connection', (ws) => {
    console.log(`✓ Client navigateur connecté (total: ${wss.clients.size})`);
    if (!aisSocket) connectToAISStream();
    sendGhostsTo(ws);

    ws.on('close', () => {
        console.log(`✗ Client déconnecté (restants: ${wss.clients.size})`);
    });

    ws.on('error', (err) => {
        console.log('✗ Erreur client:', err.message);
    });
});

// ============================================================
// DÉMARRAGE
// ============================================================
loadGhostBoats();
watchGhostsFile();

httpServer.listen(PORT, () => {
    console.log('');
    console.log('═══════════════════════════════════════════════════');
    console.log('  🌊 Radar Maritime Réunion — Serveur local');
    console.log('═══════════════════════════════════════════════════');
    console.log(`  HTTP      : http://localhost:${PORT}`);
    console.log(`  WebSocket : ws://localhost:${PORT}/ws`);
    console.log(`  Ghosts    : ${ghostBoats.length} (scène ${ghostScene || '?'})`);
    console.log('═══════════════════════════════════════════════════');
    console.log('');
});

process.on('SIGINT', () => {
    console.log('\n→ Arrêt du serveur...');
    if (aisSocket) aisSocket.close();
    wss.close();
    httpServer.close();
    process.exit(0);
});