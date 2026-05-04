const express = require('express');
const router = express.Router();

const pool = require('../db');
const { verifyToken } = require('../middleware/auth');
const { sendSuccess, sendError } = require('../utils/response');
const { parseNumericValue } = require('../utils/validators');

const to_notification_response = (row) => ({
    noti_id: row.noti_id,
    mem_id: row.mem_id,
    activity_id: row.activity_id,
    noti_title: row.noti_title,
    noti_msg: row.noti_msg,
    is_received: row.is_received,
    noti_type: row.noti_type,
    created_at: row.created_at
});

router.post('/fcm-token', verifyToken, async (req, res) => {
    const mem_id = req.user.mem_id;
    const { fcm_token } = req.body;

    if (!fcm_token || !String(fcm_token).trim()) {
        return sendError(res, 400, 'fcm_token is required.');
    }

    try {
        await pool.query(
            `
            INSERT INTO push_tokens (mem_id, fcm_token, is_active, updated_at)
            VALUES ($1, $2, TRUE, CURRENT_TIMESTAMP)
            ON CONFLICT (fcm_token)
            DO UPDATE SET
                mem_id = EXCLUDED.mem_id,
                is_active = TRUE,
                updated_at = CURRENT_TIMESTAMP
            `,
            [mem_id, String(fcm_token).trim()]
        );

        return sendSuccess(res, 200, { message: 'FCM token registered.' });
    } catch (err) {
        console.error('FCM token update error:', err);
        return sendError(res, 500, 'Server error while updating FCM token.');
    }
});

router.get('/', verifyToken, async (req, res) => {
    const mem_id = req.user.mem_id;

    try {
        const query = `
            SELECT
                noti_id,
                mem_id,
                activity_id,
                noti_title,
                noti_msg,
                is_received,
                noti_type,
                created_at
            FROM notifications
            WHERE mem_id = $1
            ORDER BY created_at DESC, noti_id DESC
        `;

        const { rows } = await pool.query(query, [mem_id]);

        return sendSuccess(res, 200, {
            notifications: rows.map(to_notification_response)
        });
    } catch (error) {
        console.error('Notification fetch error:', error);
        return sendError(res, 500, 'Server error while fetching notifications.');
    }
});

router.get('/unread-count', verifyToken, async (req, res) => {
    const mem_id = req.user.mem_id;
    try {
        const { rows } = await pool.query(
            'SELECT COUNT(*)::int AS count FROM notifications WHERE mem_id = $1 AND is_received = FALSE',
            [mem_id]
        );
        return sendSuccess(res, 200, { count: rows[0].count });
    } catch (error) {
        console.error('Notification unread count error:', error);
        return sendError(res, 500, 'Server error while fetching unread count.');
    }
});

router.patch('/read-all', verifyToken, async (req, res) => {
    const mem_id = req.user.mem_id;

    try {
        const update_query = `
            UPDATE notifications
            SET
                is_received = TRUE,
                received_time = CURRENT_TIMESTAMP
            WHERE mem_id = $1
              AND is_received = FALSE
            RETURNING
                noti_id
        `;

        const { rows } = await pool.query(update_query, [mem_id]);

        return sendSuccess(res, 200, {
            message: 'All notifications marked as received.',
            count: rows.length
        });
    } catch (error) {
        console.error('Notification read-all error:', error);
        return sendError(res, 500, 'Server error while updating notifications.');
    }
});

router.patch('/:id/read', verifyToken, async (req, res) => {
    const mem_id = req.user.mem_id;
    const parsed_noti_id = parseNumericValue(req.params.id);

    if (parsed_noti_id === null) {
        return sendError(res, 400, 'Invalid notification id.');
    }

    try {
        const update_query = `
            UPDATE notifications
            SET
                is_received = TRUE,
                received_time = CURRENT_TIMESTAMP
            WHERE noti_id = $1
              AND mem_id = $2
            RETURNING
                noti_id,
                mem_id,
                activity_id,
                noti_title,
                noti_msg,
                is_received,
                noti_type,
                created_at
        `;

        const { rows } = await pool.query(update_query, [
            parsed_noti_id,
            mem_id
        ]);

        if (rows.length === 0) {
            return sendError(res, 404, 'Notification not found or access denied.');
        }

        return sendSuccess(res, 200, {
            message: 'Notification marked as received.',
            notification: to_notification_response(rows[0])
        });
    } catch (error) {
        console.error('Notification read error:', error);
        return sendError(res, 500, 'Server error while updating notification.');
    }
});

module.exports = router;
