const fs = require('fs');
const path = require('path');
const { initFirestore } = require('./firestore_auth_state');
const { FieldValue } = require('firebase-admin/firestore');

/**
 * Migration Utility: Uploads existing local Baileys session files ('baileys_auth_info')
 * to Google Cloud Firestore (supports either 'wa_sessions' or custom 'apps-bot' collection).
 */

async function migrateSession(targetCollection = 'wa_sessions', targetDoc = 'session_081808630730') {
    const authDir = path.join(__dirname, 'baileys_auth_info');
    if (!fs.existsSync(authDir)) {
        console.error(`[MIGRATE ERROR] Folder sesi lokal '${authDir}' tidak ditemukan.`);
        process.exit(1);
    }

    console.log(`[MIGRATE] Menyiapkan migrasi dari ${authDir}...`);
    console.log(`[MIGRATE] Target Firestore: Collection: '${targetCollection}', Doc: '${targetDoc}'`);

    const db = initFirestore();
    const sessionDocRef = db.collection(targetCollection).doc(targetDoc);
    const keysColRef = sessionDocRef.collection('keys');

    const files = fs.readdirSync(authDir);
    console.log(`[MIGRATE] Ditemukan ${files.length} file sesi lokal.`);

    let successCount = 0;
    let errorCount = 0;

    for (const file of files) {
        try {
            const filePath = path.join(authDir, file);
            const content = fs.readFileSync(filePath, 'utf-8');

            if (file === 'creds.json') {
                await sessionDocRef.set({
                    data: content,
                    migratedAt: FieldValue.serverTimestamp(),
                    fileName: file
                }, { merge: true });
                console.log(`[MIGRATE] ✓ Berhasil mengunggah creds.json ke dokumen utama.`);
            } else {
                const keyDocId = file.replace(/\.json$/, '').replace(/[\/\.]/g, '__');
                await keysColRef.doc(keyDocId).set({
                    data: content,
                    migratedAt: FieldValue.serverTimestamp(),
                    fileName: file
                });
            }
            successCount++;
        } catch (err) {
            errorCount++;
            console.error(`[MIGRATE ERROR] Gagal mengunggah ${file}:`, err.message);
        }
    }

    console.log(`\n======================================================`);
    console.log(`🎉 MIGRASI SELESAI! Berhasil: ${successCount}, Gagal: ${errorCount}`);
    console.log(`Path Terpetakan: /${targetCollection}/${targetDoc}`);
    console.log(`======================================================\n`);
}

// Argument parsing: node migrate_to_firestore.js [collection] [docId]
const targetCol = process.argv[2] || process.env.WA_FIRESTORE_COLLECTION || 'wa_sessions';
const targetDoc = process.argv[3] || process.env.WA_FIRESTORE_DOC_ID || 'session_081808630730';

migrateSession(targetCol, targetDoc).catch(console.error);
