const express = require('express');
const fs = require('fs');
const path = require('path');
const multer = require('multer');
const jwt = require('jsonwebtoken');
const router = express.Router();

const pool = require('../db');
const { verifyToken } = require('../middleware/auth');
const { find_patient_id_by_mem_id } = require('../utils/auth-user');
const { sendSuccess, sendError } = require('../utils/response');
const { is_device_online } = require('../utils/device-status');

// ─── 알림음 업로드 multer ─────────────────────────────────────────────────────
const SOUND_UPLOAD_DIR = path.join(__dirname, '..', 'uploads', 'sounds');
fs.mkdirSync(SOUND_UPLOAD_DIR, { recursive: true });

const sound_upload = multer({
    storage: multer.diskStorage({
        destination: (_req, _file, cb) => cb(null, SOUND_UPLOAD_DIR),
        filename: (_req, file, cb) => {
            const ext = path.extname(file.originalname) || '.mp3';
            cb(null, `alarm_${Date.now()}${ext}`);
        },
    }),
    limits: { fileSize: 20 * 1024 * 1024 }, // 20 MB
    fileFilter: (_req, file, cb) => {
        if (file.mimetype.startsWith('audio/')) return cb(null, true);
        cb(new Error('오디오 파일만 업로드할 수 있습니다'));
    },
});

const to_device_response = (row) => ({
    device_id: row.device_id,
    device_uid: row.device_uid,
    patient_id: row.patient_id,
    device_status: row.device_status,
    last_ping: row.last_ping,
    is_connected: is_device_online(row.last_ping),
    registered_at: row.registered_at
});

const touch_device_last_ping_by_device_id = async (executor, device_id) => {
    const query = `
        UPDATE devices
        SET last_ping = CURRENT_TIMESTAMP
        WHERE device_id = $1
        RETURNING
            device_id,
            device_uid,
            patient_id,
            device_status,
            last_ping,
            registered_at
    `;

    const { rows } = await executor.query(query, [device_id]);
    return rows[0] || null;
};

router.post('/ping', async (req, res) => {
    const { device_uid } = req.body;

    if (!device_uid || !String(device_uid).trim()) {
        return sendError(res, 400, 'device_uid is required.');
    }

    try {
        const update_query = `
            UPDATE devices
            SET last_ping = CURRENT_TIMESTAMP
            WHERE device_uid = $1
            RETURNING
                device_id,
                device_uid,
                patient_id,
                device_status,
                last_ping,
                registered_at
        `;

        const { rows } = await pool.query(update_query, [String(device_uid).trim()]);

        if (rows.length === 0) {
            return sendError(res, 404, 'Device not found.');
        }

        return sendSuccess(res, 200, {
            message: 'Device ping updated successfully.',
            device: to_device_response(rows[0])
        });
    } catch (error) {
        console.error('Device ping error:', error);
        return sendError(res, 500, 'Server error while updating device ping.');
    }
});

// GET /api/device/fingerprints?device_uid=...  — 등록된 지문 목록 조회
router.get('/fingerprints', async (req, res) => {
    const { device_uid } = req.query;
    if (!device_uid || !String(device_uid).trim()) {
        return sendError(res, 400, 'device_uid is required.');
    }
    try {
        const { rows } = await pool.query(`
            SELECT p.fingerprint_slots
            FROM patients p
            JOIN devices d ON d.patient_id = p.patient_id
            WHERE d.device_uid = $1
            LIMIT 1
        `, [String(device_uid).trim()]);
        const fingerprints = rows[0]?.fingerprint_slots ?? [];
        return sendSuccess(res, 200, { fingerprints });
    } catch (err) {
        console.error('Fingerprint list error:', err);
        return sendError(res, 500, 'Server error while listing fingerprints.');
    }
});

// POST /api/device/fingerprints  — 새 지문 슬롯 등록 (patients.fingerprint_slots JSONB 배열에 추가)
router.post('/fingerprints', async (req, res) => {
    const { device_uid, slot_id, label } = req.body;
    if (!device_uid || !String(device_uid).trim()) {
        return sendError(res, 400, 'device_uid is required.');
    }
    if (slot_id === undefined || slot_id === null) {
        return sendError(res, 400, 'slot_id is required.');
    }
    const parsed_slot = parseInt(slot_id, 10);
    if (isNaN(parsed_slot) || parsed_slot < 0) {
        return sendError(res, 400, 'slot_id must be a non-negative integer.');
    }
    try {
        const { rows: dev_rows } = await pool.query(
            'SELECT patient_id FROM devices WHERE device_uid = $1 AND patient_id IS NOT NULL LIMIT 1',
            [String(device_uid).trim()]
        );
        if (!dev_rows.length) {
            return sendError(res, 404, 'Device not found or not assigned to a patient.');
        }
        const patient_id = dev_rows[0].patient_id;
        const new_entry = {
            slot_id: parsed_slot,
            label: label || '지문',
            registered_at: new Date().toISOString(),
        };
        // 동일 slot_id 기존 항목 제거 후 새 항목 추가 (upsert 효과)
        const { rows } = await pool.query(`
            UPDATE patients
            SET fingerprint_slots = (
                SELECT COALESCE(jsonb_agg(elem ORDER BY (elem->>'registered_at')), '[]'::jsonb)
                FROM jsonb_array_elements(fingerprint_slots) AS elem
                WHERE (elem->>'slot_id')::int != $1
            ) || $2::jsonb
            WHERE patient_id = $3
            RETURNING fingerprint_slots
        `, [parsed_slot, JSON.stringify([new_entry]), patient_id]);
        return sendSuccess(res, 201, { fingerprint: new_entry, fingerprints: rows[0].fingerprint_slots });
    } catch (err) {
        console.error('Fingerprint register error:', err);
        return sendError(res, 500, 'Server error while registering fingerprint.');
    }
});

// DELETE /api/device/fingerprints/:slot_id?device_uid=...  — 특정 슬롯 삭제
router.delete('/fingerprints/:slot_id', async (req, res) => {
    const { device_uid } = req.query;
    const parsed_slot = parseInt(req.params.slot_id, 10);
    if (!device_uid || !String(device_uid).trim()) {
        return sendError(res, 400, 'device_uid is required.');
    }
    if (isNaN(parsed_slot)) {
        return sendError(res, 400, 'slot_id must be an integer.');
    }
    try {
        const { rows } = await pool.query(`
            UPDATE patients
            SET fingerprint_slots = (
                SELECT COALESCE(jsonb_agg(elem ORDER BY (elem->>'registered_at')), '[]'::jsonb)
                FROM jsonb_array_elements(fingerprint_slots) AS elem
                WHERE (elem->>'slot_id')::int != $1
            )
            WHERE patient_id = (
                SELECT patient_id FROM devices
                WHERE device_uid = $2 AND patient_id IS NOT NULL LIMIT 1
            )
            RETURNING fingerprint_slots
        `, [parsed_slot, String(device_uid).trim()]);
        if (!rows.length) {
            return sendError(res, 404, 'Device not found or not assigned to a patient.');
        }
        return sendSuccess(res, 200, { message: 'Fingerprint deleted.', fingerprints: rows[0].fingerprint_slots });
    } catch (err) {
        console.error('Fingerprint delete error:', err);
        return sendError(res, 500, 'Server error while deleting fingerprint.');
    }
});

// POST /api/device/fingerprint  — JWT 불필요, device_uid 로 인증
router.post('/fingerprint', async (req, res) => {
    const { device_uid, fingerprint_id } = req.body;

    if (!device_uid || !String(device_uid).trim()) {
        return sendError(res, 400, 'device_uid is required.');
    }

    if (fingerprint_id === undefined || fingerprint_id === null) {
        return sendError(res, 400, 'fingerprint_id is required.');
    }

    const parsed_id = parseInt(fingerprint_id, 10);
    if (isNaN(parsed_id) || parsed_id < 0) {
        return sendError(res, 400, 'fingerprint_id must be a non-negative integer.');
    }

    try {
        const { rows } = await pool.query(`
            UPDATE patients
            SET fingerprint_id = $1
            WHERE patient_id = (
                SELECT patient_id FROM devices
                WHERE device_uid = $2
                  AND patient_id IS NOT NULL
                LIMIT 1
            )
            RETURNING patient_id, fingerprint_id
        `, [parsed_id, String(device_uid).trim()]);

        if (rows.length === 0) {
            return sendError(res, 404, 'Device not found or not assigned to a patient.');
        }

        return sendSuccess(res, 200, {
            message: 'Fingerprint ID saved successfully.',
            patient_id: rows[0].patient_id,
            fingerprint_id: rows[0].fingerprint_id
        });
    } catch (error) {
        console.error('Fingerprint update error:', error);
        return sendError(res, 500, 'Server error while saving fingerprint ID.');
    }
});

router.post('/register', verifyToken, async (req, res) => {
    const mem_id = req.user.mem_id;
    const { device_uid, deviceName, device_name } = req.body;

    if (!device_uid || !String(device_uid).trim()) {
        return sendError(res, 400, 'device_uid is required.');
    }

    try {
        const patient_id = await find_patient_id_by_mem_id(mem_id);

        if (!patient_id) {
            return sendError(res, 404, 'Patient not found.');
        }

        const find_device_query = `
            SELECT
                device_id,
                device_uid,
                patient_id,
                device_status,
                last_ping,
                registered_at
            FROM devices
            WHERE device_uid = $1
            LIMIT 1
        `;
        const normalized_device_uid = String(device_uid).trim();
        const normalized_device_name = String(device_name || deviceName || '').trim();
        const device_result = await pool.query(find_device_query, [normalized_device_uid]);

        if (device_result.rows.length === 0) {
            const existing_my_device_query = `
                SELECT
                    device_id,
                    device_uid,
                    patient_id,
                    device_status,
                    last_ping,
                    registered_at
                FROM devices
                WHERE patient_id = $1
                LIMIT 1
            `;
            const existing_my_device_result = await pool.query(existing_my_device_query, [patient_id]);

            if (existing_my_device_result.rows.length > 0) {
                return sendError(res, 409, 'A device is already assigned to this patient.', {
                    device: to_device_response(existing_my_device_result.rows[0])
                });
            }

            console.log('[DEVICE-REGISTER] creating new device row:', {
                mem_id,
                patient_id,
                device_uid: normalized_device_uid
            });

            const insert_query = `
                INSERT INTO devices (
                    device_uid,
                    patient_id,
                    device_status,
                    registered_at,
                    last_ping,
                    device_name
                )
                VALUES ($1, $2, 'REGISTERED', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, COALESCE(NULLIF($3, ''), 'UNKNOWN'))
                RETURNING
                    device_id,
                    device_uid,
                    patient_id,
                    device_status,
                    last_ping,
                    registered_at
            `;

            const { rows } = await pool.query(insert_query, [
                normalized_device_uid,
                patient_id,
                normalized_device_name
            ]);

            return sendSuccess(res, 201, {
                message: 'Device registered successfully.',
                device: to_device_response(rows[0])
            });
        }

        const device = device_result.rows[0];

        if (device.patient_id && device.patient_id !== patient_id) {
            return sendError(res, 409, 'Device is already assigned to another patient.');
        }

        if (device.patient_id === patient_id) {
            const touched_device = await touch_device_last_ping_by_device_id(pool, device.device_id);
            return sendSuccess(res, 200, {
                message: 'Device is already assigned to this patient.',
                device: to_device_response(touched_device || device)
            });
        }

        const existing_my_device_query = `
            SELECT
                device_id,
                device_uid,
                patient_id,
                device_status,
                last_ping,
                registered_at
            FROM devices
            WHERE patient_id = $1
            LIMIT 1
        `;
        const existing_my_device_result = await pool.query(existing_my_device_query, [patient_id]);

        if (existing_my_device_result.rows.length > 0) {
            return sendError(res, 409, 'A device is already assigned to this patient.', {
                device: to_device_response(existing_my_device_result.rows[0])
            });
        }

        const update_query = `
            UPDATE devices
            SET
                patient_id = $1,
                device_status = 'REGISTERED',
                registered_at = CURRENT_TIMESTAMP,
                last_ping = CURRENT_TIMESTAMP,
                device_name = COALESCE(NULLIF($3, ''), device_name, 'UNKNOWN')
            WHERE device_uid = $2
            RETURNING
                device_id,
                device_uid,
                patient_id,
                device_status,
                last_ping,
                registered_at
        `;

        const { rows } = await pool.query(update_query, [
            patient_id,
            normalized_device_uid,
            normalized_device_name
        ]);

        return sendSuccess(res, 200, {
            message: 'Device registered successfully.',
            device: to_device_response(rows[0])
        });
    } catch (error) {
        console.error('Device register error:', error);
        return sendError(res, 500, 'Server error while registering device.');
    }
});

router.get('/me', verifyToken, async (req, res) => {
    const mem_id = req.user.mem_id;

    try {
        const patient_id = await find_patient_id_by_mem_id(mem_id);

        if (!patient_id) {
            return sendError(res, 404, 'Patient not found.');
        }

        const query = `
            SELECT
                device_id,
                device_uid,
                patient_id,
                device_status,
                last_ping,
                registered_at
            FROM devices
            WHERE patient_id = $1
            LIMIT 1
        `;

        const { rows } = await pool.query(query, [patient_id]);

        if (rows.length === 0) {
            return sendError(res, 404, 'Device not found.');
        }

        return sendSuccess(res, 200, {
            device: to_device_response(rows[0])
        });
    } catch (error) {
        console.error('Device fetch error:', error);
        return sendError(res, 500, 'Server error while fetching device.');
    }
});

router.delete('/me', verifyToken, async (req, res) => {
    const mem_id = req.user.mem_id;

    try {
        const patient_id = await find_patient_id_by_mem_id(mem_id);

        if (!patient_id) {
            return sendError(res, 404, 'Patient not found.');
        }

        const update_query = `
            UPDATE devices
            SET
                device_status = 'UNREGISTERED'
            WHERE patient_id = $1
            RETURNING
                device_id,
                device_uid,
                patient_id,
                device_status,
                last_ping,
                registered_at
        `;

        const { rows } = await pool.query(update_query, [patient_id]);

        if (rows.length === 0) {
            return sendError(res, 404, 'Device not found.');
        }

        return sendSuccess(res, 200, {
            message: 'Device unregistered successfully.',
            device: to_device_response(rows[0])
        });
    } catch (error) {
        console.error('Device unregister error:', error);
        return sendError(res, 500, 'Server error while unregistering device.');
    }
});

// GET /api/device/sound  — 알림음 메타 조회
//   Raspberry Pi: ?device_uid=XXX (인증 불필요)
//   프론트엔드:   Authorization: Bearer <token>
router.get('/sound', async (req, res) => {
    const { device_uid } = req.query;
    const auth_header = req.headers.authorization;

    try {
        let row;

        if (device_uid) {
            const { rows } = await pool.query(
                `SELECT alarm_sound_path, alarm_sound_name, alarm_sound_updated_at
                 FROM devices WHERE device_uid = $1 LIMIT 1`,
                [String(device_uid).trim()]
            );
            row = rows[0];
        } else if (auth_header?.startsWith('Bearer ')) {
            const decoded = jwt.verify(auth_header.slice(7), process.env.JWT_SECRET);
            const patient_id = await find_patient_id_by_mem_id(decoded.mem_id);
            if (!patient_id) return sendError(res, 404, 'Patient not found.');
            const { rows } = await pool.query(
                `SELECT alarm_sound_path, alarm_sound_name, alarm_sound_updated_at
                 FROM devices WHERE patient_id = $1 LIMIT 1`,
                [patient_id]
            );
            row = rows[0];
        } else {
            return sendError(res, 400, 'device_uid or Authorization required.');
        }

        if (!row?.alarm_sound_path) {
            return sendSuccess(res, 200, { sound: null });
        }

        return sendSuccess(res, 200, {
            sound: {
                file_name: row.alarm_sound_name,
                file_path: row.alarm_sound_path,
                updated_at: row.alarm_sound_updated_at,
            }
        });
    } catch (err) {
        if (err.name === 'JsonWebTokenError' || err.name === 'TokenExpiredError') {
            return sendError(res, 401, 'Invalid or expired token.');
        }
        console.error('Sound fetch error:', err);
        return sendError(res, 500, 'Server error while fetching sound.');
    }
});

// POST /api/device/sound  — 알림음 업로드 (프론트엔드, JWT 필요)
router.post('/sound', verifyToken, sound_upload.single('sound'), async (req, res) => {
    if (!req.file) return sendError(res, 400, '업로드된 파일이 없습니다.');

    const remove_file = (p) => { try { fs.unlinkSync(p); } catch {} };

    try {
        const patient_id = await find_patient_id_by_mem_id(req.user.mem_id);
        if (!patient_id) {
            remove_file(req.file.path);
            return sendError(res, 404, 'Patient not found.');
        }

        // 기존 파일 삭제
        const { rows: old } = await pool.query(
            'SELECT alarm_sound_path FROM devices WHERE patient_id = $1 LIMIT 1',
            [patient_id]
        );
        if (old[0]?.alarm_sound_path) {
            remove_file(path.join(__dirname, '..', old[0].alarm_sound_path));
        }

        const relative_path = path.join('uploads', 'sounds', req.file.filename).replace(/\\/g, '/');

        const { rows } = await pool.query(
            `UPDATE devices
             SET alarm_sound_path = $1,
                 alarm_sound_name = $2,
                 alarm_sound_updated_at = NOW()
             WHERE patient_id = $3
             RETURNING alarm_sound_name, alarm_sound_path, alarm_sound_updated_at`,
            [relative_path, req.file.originalname, patient_id]
        );

        if (!rows.length) {
            remove_file(req.file.path);
            return sendError(res, 404, 'Device not found.');
        }

        return sendSuccess(res, 201, {
            sound: {
                file_name: rows[0].alarm_sound_name,
                file_path: rows[0].alarm_sound_path,
                updated_at: rows[0].alarm_sound_updated_at,
            }
        });
    } catch (err) {
        remove_file(req.file.path);
        console.error('Sound upload error:', err);
        return sendError(res, 500, 'Server error while uploading sound.');
    }
});

module.exports = router;
