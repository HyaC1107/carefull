const express = require('express');
const router = express.Router();

const { verifyToken } = require('../middleware/auth');
const { sendSuccess, sendError } = require('../utils/response');
const {
    register_push_token,
    send_test_push
} = require('../services/push.service');

router.post('/register', verifyToken, async (req, res) => {
    const mem_id = req.user.mem_id;
    const fcm_token = String(req.body?.fcm_token || '').trim();
    const device_type = String(req.body?.device_type || 'web').trim() || 'web';

    if (!fcm_token) {
        return sendError(res, 400, 'fcm_token is required.');
    }

    try {
        const push_token = await register_push_token({
            mem_id,
            fcm_token,
            device_type
        });

        return sendSuccess(res, 200, {
            message: 'Push token registered successfully.',
            push_token
        });
    } catch (error) {
        console.error('Push token register error:', error);
        return sendError(res, 500, 'Server error while registering push token.');
    }
});

router.post('/test', verifyToken, async (req, res) => {
    const mem_id = req.user.mem_id;

    try {
        const result = await send_test_push(mem_id);

        return sendSuccess(res, 200, {
            message: 'Push test completed.',
            result
        });
    } catch (error) {
        console.error('Push test error:', error);
        return sendError(res, 500, 'Server error while sending push test.');
    }
});

module.exports = router;
