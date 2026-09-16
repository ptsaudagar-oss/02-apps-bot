const { default: makeWASocket, useMultiFileAuthState, DisconnectReason } = require('@whiskeysockets/baileys');
const qrcode = require('qrcode-terminal');
const express = require('express');
const pino = require('pino');

const app = express();
app.use(express.json());

const PORT = 3000;
let sock = null;
let isConnected = false;
let lastQr = '';

async function startWhatsApp() {
    const { state, saveCreds } = await useMultiFileAuthState('baileys_auth_info');
    
    sock = makeWASocket({
        auth: state,
        printQRInTerminal: true,
        logger: pino({ level: 'silent' })
    });

    sock.ev.on('creds.update', saveCreds);

    sock.ev.on('connection.update', (update) => {
        const { connection, lastDisconnect, qr } = update;
        if (qr) {
            lastQr = qr;
            console.log('\n======================================================');
            console.log('📌 SCAN QR CODE DI BAWAH INI DENGAN WHATSAPP 081808630730:');
            console.log('======================================================\n');
            qrcode.generate(qr, { small: true });
            console.log('\nAtau buka browser di: http://127.0.0.1:3000/qr');
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
            console.log('\n🎉 [SUKSES] WHATSAPP LOCAL GATEWAY BERHASIL TERHUBUNG DENGAN NOMOR ANDA!');
            isConnected = true;
            lastQr = '';
        }
    });
}

// Endpoint status
app.get('/status', (req, res) => {
    res.json({
        status: isConnected ? 'CONNECTED' : 'WAITING_FOR_SCAN',
        port: PORT,
        qr_available: Boolean(lastQr)
    });
});

// Endpoint untuk melihat teks raw QR
app.get('/qr', (req, res) => {
    if (isConnected) {
        return res.send('<h3>WhatsApp sudah terhubung! Silakan gunakan sistem.</h3>');
    }
    if (!lastQr) {
        return res.send('<h3>Sedang menginisialisasi QR Code, silakan refresh sebentar lagi...</h3>');
    }
    res.send(`
        <html>
        <head><title>Scan QR WhatsApp Local Gateway</title></head>
        <body style="font-family: sans-serif; text-align: center; padding: 40px;">
            <h2>Scan QR Code WhatsApp Gateway (Port 3000)</h2>
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
        console.log(`[LOCAL GATEWAY] Pesan fisik terkirim ke ${cleanTo}`);
        res.json({ success: true, messageId: sent.key.id, to: cleanTo });
    } catch (err) {
        console.error('[LOCAL GATEWAY ERROR]', err);
        res.status(500).json({ success: false, error: err.message });
    }
});

app.listen(PORT, () => {
    console.log(`[LOCAL GATEWAY] Server berjalan di http://127.0.0.1:${PORT}`);
    startWhatsApp();
});
