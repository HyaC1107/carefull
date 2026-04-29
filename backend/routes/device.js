const express = require('express');
const router = express.Router();

const pool = require('../db');
const { verifyToken } = require('../middleware/auth');
const { find_patient_id_by_mem_id } = require('../utils/auth-user');
const { sendSuccess, sendError } = require('../utils/response');
const { is_device_online } = require('../utils/device-status');

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
            SELECT f.fp_id, f.slot_id, f.label, f.registered_at
            FROM fingerprints f
            JOIN devices d ON d.patient_id = f.patient_id
            WHERE d.device_uid = $1
            ORDER BY f.registered_at ASC
        `, [String(device_uid).trim()]);
        return sendSuccess(res, 200, { fingerprints: rows });
    } catch (err) {
        console.error('Fingerprint list error:', err);
        return sendError(res, 500, 'Server error while listing fingerprints.');
    }
});

// POST /api/device/fingerprints  — 새 지문 슬롯 등록
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
        const { rows } = await pool.query(`
            INSERT INTO fingerprints (patient_id, slot_id, label)
            VALUES ($1, $2, $3)
            ON CONFLICT (patient_id, slot_id)
            DO UPDATE SET label = EXCLUDED.label, registered_at = CURRENT_TIMESTAMP
            RETURNING fp_id, slot_id, label, registered_at
        `, [patient_id, parsed_slot, label || '지문']);
        return sendSuccess(res, 201, { fingerprint: rows[0] });
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
            DELETE FROM fingerprints
            WHERE slot_id = $1
              AND patient_id = (
                SELECT patient_id FROM devices
                WHERE device_uid = $2 AND patient_id IS NOT NULL LIMIT 1
              )
            RETURNING fp_id, slot_id
        `, [parsed_slot, String(device_uid).trim()]);
        if (!rows.length) {
            return sendError(res, 404, 'Fingerprint not found.');
        }
        return sendSuccess(res, 200, { message: 'Fingerprint deleted.', fp_id: rows[0].fp_id });
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

// GET /api/device/sound?device_uid=...  — 라파용, 현재 알림음 메타 조회
router.get('/sound', async (req, res) => {
    const { device_uid } = req.query;
    if (!device_uid || !String(device_uid).trim()) {
        return sendError(res, 400, 'device_uid is required.');
    }
    try {
        const { rows } = await pool.query(`
            SELECT vs.file_path, vs.uploaded_at
            FROM voice_samples vs
            JOIN devices d ON d.patient_id = vs.patient_id
            WHERE d.device_uid = $1
              AND vs.status IN ('pending', 'ready')
            ORDER BY vs.uploaded_at DESC
            LIMIT 1
        `, [String(device_uid).trim()]);

        if (!rows.length) {
            return sendSuccess(res, 200, { sound: null });
        }

        return sendSuccess(res, 200, {
            sound: {
                file_path: rows[0].file_path,   // "uploads/voices/filename.ext"
                updated_at: rows[0].uploaded_at,
            }
        });
    } catch (err) {
        console.error('Sound fetch error:', err);
        return sendError(res, 500, 'Server error while fetching sound.');
    }
});

module.exports = router;
