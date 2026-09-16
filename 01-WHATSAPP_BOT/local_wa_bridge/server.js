const { default: makeWASocket, useMultiFileAuthState, DisconnectReason } = require('@whiskeysockets/baileys');
const { useFirestoreAuthState } = require('./firestore_auth_state');
const qrcode = require('qrcode-terminal');
const express = require('express');
const pino = require('pino');
const fs = require('fs');
const path = require('path');

const app = express();
app.use(express.json());

const PORT = process.env.PORT || 3000;
const SESSION_ID = process.env.WA_SESSION_ID || 'session_081808630730';
const USE_FIRESTORE_AUTH = process.env.WA_USE_FIRESTORE !== 'false'; // default true if configured

let sock = null;
let isConnected = false;
let lastQr = '';
let activeAuthBackend = 'local';

/**
 * Memilih dan menginisialisasi auth backend:
 * 1. Coba Firestore Auth State terlebih dahulu jika diaktifkan
 * 2. Jika gagal atau dinonaktifkan, fallback otomatis ke Local multi-file auth state ('baileys_auth_info')
 */
async function resolveAuthState() {
    if (USE_FIRESTORE_AUTH) {
        try {
            console.log(`[AUTH] Menghubungkan sesi WhatsApp ke Google Cloud Firestore (ID: ${SESSION_ID})...`);
            const firestoreAuth = await useFirestoreAuthState(SESSION_ID);
            activeAuthBackend = 'firestore';
            console.log(`[AUTH] ✓ Berhasil menggunakan backend Firestore Auth State.`);
            return firestoreAuth;
        } catch (err) {
            console.warn(`[AUTH WARN] Gagal inisialisasi Firestore Auth (${err.message}). Mengaktifkan fallback lokal...`);
        }
    }

    console.log('[AUTH] Menggunakan Local Multi-File Auth State (baileys_auth_info)...');
    activeAuthBackend = 'local';
    return await useMultiFileAuthState('baileys_auth_info');
}

async function startWhatsApp() {
    try {
        const { state, saveCreds } = await resolveAuthState();
        
        sock = makeWASocket({
            auth: state,
            printQRInTerminal: true,
            logger: pino({ level: 'silent' })
        });

        sock.ev.on('creds.update', async () => {
            try {
                await saveCreds();
            } catch (err) {
                console.error('[AUTH ERROR] Gagal menyimpan kredensial:', err.message);
            }
        });

        sock.ev.on('connection.update', (update) => {
            const { connection, lastDisconnect, qr } = update;
            if (qr) {
                lastQr = qr;
                console.log('\n======================================================');
                console.log('📌 SCAN QR CODE DI BAWAH INI DENGAN WHATSAPP 081808630730:');
                console.log('======================================================\n');
                qrcode.generate(qr, { small: true });
                console.log(`\nAtau buka browser di: http://127.0.0.1:${PORT}/qr`);
                console.log('======================================================\n');
            }

            if (connection === 'close') {
                const shouldReconnect = (lastDisconnect?.error)?.output?.statusCode !== DisconnectReason.loggedOut;
                console.log('Koneksi terputus. Mencoba reconnect:', shouldReconnect);
                isConnected = false;
                if (shouldReconnect) {
                    startWhatsApp();
                }
            } else if (connection === 'open') {
                console.log(`\n🎉 [SUKSES] WHATSAPP GATEWAY BERHASIL TERHUBUNG! [Backend: ${activeAuthBackend.toUpperCase()}]`);
                isConnected = true;
                lastQr = '';
            }
        });
    } catch (err) {
        console.error('[GATEWAY FATAL ERROR] Gagal memulai WhatsApp socket:', err);
    }
}

// Endpoint status
app.get('/status', (req, res) => {
    res.json({
        status: isConnected ? 'CONNECTED' : 'WAITING_FOR_SCAN',
        port: PORT,
        auth_backend: activeAuthBackend,
        session_id: SESSION_ID,
        qr_available: Boolean(lastQr)
    });
});

// Endpoint untuk melihat visual QR Code
app.get('/qr', (req, res) => {
    if (isConnected) {
        return res.send(`<h3>WhatsApp sudah terhubung via backend ${activeAuthBackend.toUpperCase()}! Silakan gunakan sistem.</h3>`);
    }
    if (!lastQr) {
        return res.send('<h3>Sedang menginisialisasi QR Code, silakan refresh sebentar lagi...</h3>');
    }
    res.send(`
        <html>
        <head><title>Scan QR WhatsApp Gateway</title></head>
        <body style="font-family: sans-serif; text-align: center; padding: 40px;">
            <h2>Scan QR Code WhatsApp Gateway (Port ${PORT})</h2>
            <p>Auth Backend Aktif: <b>${activeAuthBackend.toUpperCase()}</b></p>
            <p>Buka WhatsApp di HP <b>081808630730</b> &gt; Perangkat Tertaut &gt; Tautkan Perangkat</p>
            <div id="qrcode" style="display: flex; justify-content: center; margin-top: 20px;"></div>
            <script src="https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js"></script>
            <script>
                new QRCode(document.getElementById("qrcode"), {
                    text: "${lastQr}",
                    width: 256,
                    height: 256
                });
                setTimeout(() => window.location.reload(), 15000);
            </script>
        </body>
        </html>
    `);
});

// Endpoint pengiriman pesan yang diakses oleh message_handler.py
app.post('/api/send', async (req, res) => {
    try {
        const to = req.body.to || req.body.phone;
        const message = req.body.message || req.body.text;

        if (!isConnected || !sock) {
            return res.status(503).json({
                success: false,
                error: 'WhatsApp belum terhubung. Silakan scan QR code terlebih dahulu.'
            });
        }

        let cleanTo = String(to).replace(/[^0-9]/g, '');
        if (cleanTo.startsWith('08')) {
            cleanTo = '628' + cleanTo.substring(2);
        }
        const jid = `${cleanTo}@s.whatsapp.net`;

        const sent = await sock.sendMessage(jid, { text: message });
        console.log(`[GATEWAY] Pesan fisik terkirim ke ${cleanTo} via ${activeAuthBackend.toUpperCase()}`);
        res.json({ success: true, messageId: sent.key.id, to: cleanTo, backend: activeAuthBackend });
    } catch (err) {
        console.error('[GATEWAY ERROR]', err);
        res.status(500).json({ success: false, error: err.message });
    }
});

app.listen(PORT, () => {
    console.log(`[LOCAL GATEWAY] Server berjalan di http://127.0.0.1:${PORT}`);
    startWhatsApp();
});
