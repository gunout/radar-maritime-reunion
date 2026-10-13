const AISSTREAM_URL = 'wss://stream.aisstream.io/v0/stream';
// Bbox réduite : La Réunion + 500 km autour
const BOUNDING_BOXES = [[[-25, 50], [-15, 60]]];
// Seulement les positions, pas les données statiques (trop volumineux)
const FILTER_MESSAGE_TYPES = ['PositionReport'];

export class AISRelay {
  constructor(state, env) {
    this.state = state;
    this.env = env;
    this.aisSocket = null;
    this.clients = new Set();
    this.reconnectTimer = null;
    this.reconnectAttempts = 0;
    this.maxReconnectDelay = 30000;
    this.messageCount = 0;
    // Buffer pour envoyer au navigateur par lots (évite la saturation)
    this.pendingMessages = [];
    this.flushTimer = null;
  }

  async fetch(request) {
    const upgradeHeader = request.headers.get('Upgrade');
    if (!upgradeHeader || upgradeHeader !== 'websocket') {
      return new Response('Expected WebSocket upgrade', { status: 426 });
    }
    const pair = new WebSocketPair();
    const [client, server] = Object.values(pair);
    this.state.acceptWebSocket(server);
    this.clients.add(server);
    this.ensureAISConnection();
    console.log('[relay] Client connecte. Total: ' + this.clients.size);
    return new Response(null, { status: 101, webSocket: client });
  }

  async webSocketMessage(ws, message) {}

  async webSocketClose(ws, code, reason, wasClean) {
    this.clients.delete(ws);
    const safeCode = (code === 1005 || code === 1006 || !code) ? 1000 : code;
    try {
      ws.close(safeCode, reason || '');
    } catch (e) {
      console.log('[relay] close failed: ' + e.message);
    }
    console.log('[relay] Client deconnecte. Restants: ' + this.clients.size);
    if (this.clients.size === 0) this.closeAISConnection();
  }

  async webSocketError(ws, error) {
    this.clients.delete(ws);
    console.warn('[relay] Erreur client:', error);
  }

  ensureAISConnection() {
    if (this.aisSocket && this.aisSocket.readyState === WebSocket.OPEN) {
      console.log('[relay] AIS deja connecte');
      return;
    }
    this.clearReconnectTimer();
    try {
      console.log('[relay] Tentative connexion AISStream...');
      this.aisSocket = new WebSocket(AISSTREAM_URL);

      this.aisSocket.addEventListener('open', () => {
        console.log('[relay] AISStream OPEN — envoi abonnement');
        this.reconnectAttempts = 0;
        const subscription = {
          APIKey: this.env.AISSTREAM_API_KEY,
          BoundingBoxes: BOUNDING_BOXES,
          FilterMessageTypes: FILTER_MESSAGE_TYPES,
        };
        const debugSub = { ...subscription, APIKey: '***' + (subscription.APIKey || '').slice(-4) };
        console.log('[relay] Subscription: ' + JSON.stringify(debugSub));
        this.aisSocket.send(JSON.stringify(subscription));
      });

      this.aisSocket.addEventListener('message', async (event) => {
        // AISStream envoie des frames binaires (Blob ou ArrayBuffer)
        let text;
        try {
          if (typeof event.data === 'string') {
            text = event.data;
          } else if (event.data instanceof Blob) {
            text = await event.data.text();
          } else if (event.data instanceof ArrayBuffer) {
            text = new TextDecoder().decode(event.data);
          } else if (event.data && typeof event.data.text === 'function') {
            text = await event.data.text();
          } else {
            text = String(event.data);
          }
        } catch (e) {
          console.log('[relay] Erreur conversion: ' + e.message);
          return;
        }

        this.messageCount++;

        // Log tous les 50 messages
        if (this.messageCount <= 3 || this.messageCount % 50 === 0) {
          console.log('[relay] Message #' + this.messageCount + ' (' + text.length + ' octets): ' + text.substring(0, 100));
        }

        // Détecte les erreurs AISStream
        if (text.includes('"error"')) {
          console.log('[relay] ERREUR AISStream: ' + text.substring(0, 300));
          this.broadcastImmediate(JSON.stringify({ type: 'error', message: text }));
          return;
        }

        // Ignore la confirmation d'abonnement
        if (text.includes('SubscriptionConfirmation')) {
          console.log('[relay] Abonnement confirme');
          return;
        }

        // Bufferise pour envoi par lots
        this.pendingMessages.push(text);
        this.scheduleFlush();
      });

      this.aisSocket.addEventListener('close', (event) => {
        console.log('[relay] AISStream CLOSE — code: ' + event.code + ' reason: ' + event.reason);
        this.aisSocket = null;
        if (this.clients.size > 0) this.scheduleReconnect();
      });

      this.aisSocket.addEventListener('error', (error) => {
        console.log('[relay] AISStream ERROR: ' + (error.message || JSON.stringify(error)));
      });
    } catch (e) {
      console.log('[relay] Exception connexion: ' + e.message);
      this.scheduleReconnect();
    }
  }

  scheduleFlush() {
    if (this.flushTimer) return;
    this.flushTimer = setTimeout(() => {
      this.flushTimer = null;
      this.flushPending();
    }, 500); // Envoie par lots toutes les 500ms
  }

  flushPending() {
    if (this.pendingMessages.length === 0) return;
    const batch = this.pendingMessages.splice(0);
    console.log('[relay] Flush ' + batch.length + ' messages vers navigateur');
    for (const text of batch) {
      this.broadcastImmediate(text);
    }
  }

  broadcastImmediate(message) {
    const toRemove = [];
    for (const ws of this.clients) {
      try {
        ws.send(message);
      } catch (e) {
        toRemove.push(ws);
      }
    }
    for (const ws of toRemove) this.clients.delete(ws);
  }

  closeAISConnection() {
    this.clearReconnectTimer();
    if (this.aisSocket) {
      try {
        this.aisSocket.close(1000, 'No more clients');
      } catch (e) {
        console.log('[relay] closeAIS failed: ' + e.message);
      }
      this.aisSocket = null;
    }
  }

  scheduleReconnect() {
    if (this.reconnectTimer) return;
    const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), this.maxReconnectDelay);
    this.reconnectAttempts++;
    console.log('[relay] Reconnexion dans ' + delay + 'ms');
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      this.ensureAISConnection();
    }, delay);
  }

  clearReconnectTimer() {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
  }
}

export default {
  async fetch(request, env) {
    const upgradeHeader = request.headers.get('Upgrade');
    if (!upgradeHeader || upgradeHeader !== 'websocket') {
      return new Response('AIS Relay - WebSocket only', { status: 200 });
    }
    const id = env.AIS_RELAY.idFromName('reunion');
    const obj = env.AIS_RELAY.get(id);
    return obj.fetch(request);
  },
};