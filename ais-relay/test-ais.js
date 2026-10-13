const WebSocket = require('ws');

// ⚠️ Remplace par ta clé API AISStream (régénère-la après ce test)
const KEY = 'ae61611195fbe8c091b06afc6f5d39453b0d5532';

const ws = new WebSocket('wss://stream.aisstream.io/v0/stream');

let msgCount = 0;
let subscriptionConfirmed = false;

ws.on('open', () => {
    console.log('>>> WebSocket OPEN');
    console.log('>>> Envoi abonnement (bbox monde entier pour test)...');
    ws.send(JSON.stringify({
        APIKey: KEY,
        BoundingBoxes: [[[-90, -180], [90, 180]]],
        FilterMessageTypes: ['PositionReport']
    }));
});

ws.on('message', (data, isBinary) => {
    msgCount++;
    const buf = Buffer.isBuffer(data) ? data : Buffer.from(data);
    const text = buf.toString('utf8');

    // Log détaillé du premier message, puis abrégé
    if (msgCount <= 3) {
        console.log(`\n>>> Message #${msgCount} | taille=${buf.length} bytes | isBinary=${isBinary}`);
        console.log(`>>> Contenu brut: ${text.substring(0, 400)}`);
    } else if (msgCount % 20 === 0) {
        console.log(`>>> #${msgCount} (${buf.length} bytes)`);
    }

    try {
        const event = JSON.parse(text);
        if (event.MessageType === 'SubscriptionConfirmation') {
            subscriptionConfirmed = true;
            console.log('>>> ✓ Abonnement confirmé. Attente des PositionReport...\n');
        } else if (event.MessageType === 'PositionReport') {
            if (msgCount === 1 || msgCount % 10 === 0) {
                const meta = event.MetaData || {};
                console.log(`>>> PositionReport: ${meta.ShipName || 'N/A'} @ ${meta.Latitude}, ${meta.Longitude}`);
            }
        } else {
            console.log(`>>> MessageType: ${event.MessageType}`);
        }
    } catch (e) {
        console.log(`>>> Parse error: ${e.message}`);
        console.log(`>>> Contenu: ${text.substring(0, 200)}`);
    }
});

ws.on('error', (e) => console.error('>>> ERREUR:', e.message));

ws.on('close', (code, reason) => {
    console.log(`\n>>> FERMÉ — code: ${code} | reason: "${reason.toString()}"`);
    console.log(`>>> Total messages reçus: ${msgCount}`);
    console.log(`>>> Subscription confirmée: ${subscriptionConfirmed ? 'OUI' : 'NON'}`);
});

// Timeout 60 secondes
setTimeout(() => {
    console.log(`\n>>> Timeout 60s — Total messages: ${msgCount}`);
    if (msgCount === 0) {
        console.log('>>> AUCUN message reçu. Problème de compte AISStream ou de connexion.');
    } else if (msgCount === 1 && subscriptionConfirmed) {
        console.log('>>> Uniquement la confirmation. AISStream n\'envoie pas de données.');
        console.log('>>> Causes possibles : compte limité, filtres trop restrictifs, ou panne AISStream.');
    } else if (msgCount > 1) {
        console.log('>>> ✓ AISStream envoie bien des données !');
    }
    process.exit(0);
}, 60000);