const { initializeApp, getApps, cert, applicationDefault } = require('firebase-admin/app');
const { getFirestore, FieldValue } = require('firebase-admin/firestore');
const { proto, initAuthCreds } = require('@whiskeysockets/baileys');

/**
 * Custom Firestore Authentication State Adapter for Baileys WhatsApp (Firebase Admin v13 Modular API)
 * Stores credentials and signal keys directly in Google Cloud Firestore.
 * 
 * Supports dynamic collection & document resolution:
 * e.g., Collection: `wa_sessions` or `apps-bot`, Document: `session_081808630730` or custom doc ID.
 */

const BufferJSON = {
    replacer: (k, value) => {
        if (Buffer.isBuffer(value) || value instanceof Uint8Array || value?.type === 'Buffer') {
            return { type: 'Buffer', data: Buffer.from(value?.data || value).toString('base64') };
        }
        return value;
    },
    reviver: (_, value) => {
        if (typeof value === 'object' && value !== null && value.type === 'Buffer' && typeof value.data === 'string') {
            return Buffer.from(value.data, 'base64');
        }
        if (typeof value === 'object' && value !== null && !Array.isArray(value)) {
            const keys = Object.keys(value);
            if (keys.length > 0 && keys.every(k => !isNaN(parseInt(k, 10)))) {
                const values = Object.values(value);
                if (values.every(v => typeof v === 'number')) {
                    return Buffer.from(values);
                }
            }
        }
        return value;
    }
};

function initFirestore() {
    if (getApps().length > 0) {
        return getFirestore();
    }

    const saBase64 = process.env.FIREBASE_SERVICE_ACCOUNT_BASE64 || process.env.FIREBASE_SERVICE_ACCOUNT;
    const saPath = process.env.FIREBASE_SERVICE_ACCOUNT_PATH;
    const projectId = process.env.FIREBASE_PROJECT_ID || 'apps-bot';

    let credential = null;
    if (saBase64) {
        try {
            const decoded = saBase64.startsWith('{') ? JSON.parse(saBase64) : JSON.parse(Buffer.from(saBase64, 'base64').toString('utf-8'));
            credential = cert(decoded);
            console.log('[Firestore Auth] Menggunakan Firebase Service Account dari environment variable.');
        } catch (e) {
            console.warn('[Firestore Auth] Gagal mem-parse FIREBASE_SERVICE_ACCOUNT JSON:', e.message);
        }
    } else if (saPath) {
        try {
            credential = cert(require(saPath));
            console.log('[Firestore Auth] Menggunakan Firebase Service Account dari path:', saPath);
        } catch (e) {
            console.warn('[Firestore Auth] Gagal membaca cert dari path:', saPath, e.message);
        }
    }

    if (!credential) {
        credential = applicationDefault();
        console.log('[Firestore Auth] Menggunakan Application Default Credentials (ADC).');
    }

    initializeApp({
        credential,
        projectId
    });

    return getFirestore();
}

async function useFirestoreAuthState(sessionId = 'session_081808630730', collectionName = 'wa_sessions') {
    const db = initFirestore();
    
    // Support path resolution: collection name and session document
    const targetCol = process.env.WA_FIRESTORE_COLLECTION || collectionName;
    const targetDoc = process.env.WA_FIRESTORE_DOC_ID || sessionId;

    console.log(`[Firestore Auth] Memetakan sesi Baileys ke Firestore path: /${targetCol}/${targetDoc}`);

    const sessionDocRef = db.collection(targetCol).doc(targetDoc);
    const keysColRef = sessionDocRef.collection('keys');

    const writeData = async (data, id) => {
        const serialized = JSON.stringify(data, BufferJSON.replacer);
        if (id === 'creds') {
            await sessionDocRef.set({ data: serialized, updatedAt: FieldValue.serverTimestamp() }, { merge: true });
        } else {
            const safeDocId = id.replace(/[\/\.]/g, '__');
            await keysColRef.doc(safeDocId).set({ data: serialized, updatedAt: FieldValue.serverTimestamp() });
        }
    };

    const readData = async (id) => {
        try {
            if (id === 'creds') {
                const doc = await sessionDocRef.get();
                if (doc.exists && doc.data()?.data) {
                    return JSON.parse(doc.data().data, BufferJSON.reviver);
                }
            } else {
                const safeDocId = id.replace(/[\/\.]/g, '__');
                const doc = await keysColRef.doc(safeDocId).get();
                if (doc.exists && doc.data()?.data) {
                    return JSON.parse(doc.data().data, BufferJSON.reviver);
                }
            }
        } catch (err) {
            console.error(`[Firestore Auth] Error membaca key ${id}:`, err.message);
        }
        return null;
    };

    const removeData = async (id) => {
        try {
            if (id === 'creds') {
                await sessionDocRef.delete();
            } else {
                const safeDocId = id.replace(/[\/\.]/g, '__');
                await keysColRef.doc(safeDocId).delete();
            }
        } catch (err) {
            console.error(`[Firestore Auth] Error menghapus key ${id}:`, err.message);
        }
    };

    let creds = await readData('creds');
    if (!creds) {
        creds = initAuthCreds();
    }

    return {
        state: {
            creds,
            keys: {
                get: async (type, ids) => {
                    const data = {};
                    await Promise.all(ids.map(async (id) => {
                        let value = await readData(`${type}-${id}`);
                        if (type === 'app-state-sync-key' && value) {
                            value = proto.Message.AppStateSyncKeyData.fromObject(value);
                        }
                        data[id] = value;
                    }));
                    return data;
                },
                set: async (data) => {
                    const tasks = [];
                    for (const category in data) {
                        for (const id in data[category]) {
                            const value = data[category][id];
                            const keyId = `${category}-${id}`;
                            tasks.push(value ? writeData(value, keyId) : removeData(keyId));
                        }
                    }
                    await Promise.all(tasks);
                }
            }
        },
        saveCreds: async () => {
            return writeData(creds, 'creds');
        }
    };
}

module.exports = {
    useFirestoreAuthState,
    initFirestore
};
