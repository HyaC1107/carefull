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
    registered_at: row.registered_at,
    created_at: row.registered_at
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
    const device_uid = req.body.device_uid ?? req.body.deviceUid;

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

router.post('/register', verifyToken, async (req, res) => {
    const mem_id = req.user.mem_id;
    const { serial_number } = req.body;

    if (!serial_number) {
        return sendError(res, 400, 'serial_number is required.');
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
        const device_result = await pool.query(find_device_query, [serial_number]);

        if (device_result.rows.length === 0) {
            return sendError(res, 404, 'Device not found.');
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
                last_ping = CURRENT_TIMESTAMP
            WHERE device_uid = $2
            RETURNING
                device_id,
                device_uid,
                patient_id,
                device_status,
                last_ping,
                registered_at
        `;

        const { rows } = await pool.query(update_query, [patient_id, serial_number]);

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

module.exports = router;
