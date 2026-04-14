const express = require('express');
const router = express.Router();

const pool = require('../db');
const { verifyToken } = require('../middleware/auth');
const { sendSuccess, sendError } = require('../utils/response');
const { parseNumericValue } = require('../utils/validators');

/**
 * GET /
 * 로그인한 사용자의 memberId 기준으로 알림 목록을 조회합니다.
 */
router.get('/', verifyToken, async (req, res) => {
    const memberId = req.user.memberId;

    try {
        const query = `
            SELECT
                notification_id,
                member_id,
                log_id,
                title,
                message,
                is_read,
                type,
                created_at
            FROM notifications
            WHERE member_id = $1
            ORDER BY created_at DESC, notification_id DESC
        `;

        const { rows } = await pool.query(query, [memberId]);

        return sendSuccess(res, 200, {
            notifications: rows
        });
    } catch (error) {
        console.error('알림 목록 조회 중 오류가 발생했습니다:', error);
        return sendError(res, 500, '알림 목록 조회 중 서버 오류가 발생했습니다.');
    }
});

/**
 * PATCH /read-all
 * 로그인한 사용자의 전체 알림을 읽음 처리합니다.
 */
router.patch('/read-all', verifyToken, async (req, res) => {
    const memberId = req.user.memberId;

    try {
        const updateQuery = `
            UPDATE notifications
            SET
                is_read = TRUE
            WHERE member_id = $1
              AND is_read = FALSE
            RETURNING
                notification_id
        `;

        const { rows } = await pool.query(updateQuery, [memberId]);

        return sendSuccess(res, 200, {
            message: '전체 알림이 읽음 처리되었습니다.',
            count: rows.length
        });
    } catch (error) {
        console.error('전체 알림 읽음 처리 중 오류가 발생했습니다:', error);
        return sendError(res, 500, '전체 알림 읽음 처리 중 서버 오류가 발생했습니다.');
    }
});

/**
 * PATCH /:id/read
 * 로그인한 사용자의 알림 1건을 읽음 처리합니다.
 */
router.patch('/:id/read', verifyToken, async (req, res) => {
    const memberId = req.user.memberId;
    const parsedNotificationId = parseNumericValue(req.params.id);

    if (parsedNotificationId === null) {
        return sendError(res, 400, '유효하지 않은 notification id입니다.');
    }

    try {
        const updateQuery = `
            UPDATE notifications
            SET
                is_read = TRUE
            WHERE notification_id = $1
              AND member_id = $2
            RETURNING
                notification_id,
                member_id,
                log_id,
                title,
                message,
                is_read,
                type,
                created_at
        `;

        const { rows } = await pool.query(updateQuery, [
            parsedNotificationId,
            memberId
        ]);

        if (rows.length === 0) {
            return sendError(res, 404, '해당 알림이 없거나 접근 권한이 없습니다.');
        }

        return sendSuccess(res, 200, {
            message: '알림이 읽음 처리되었습니다.',
            notification: rows[0]
        });
    } catch (error) {
        console.error('알림 읽음 처리 중 오류가 발생했습니다:', error);
        return sendError(res, 500, '알림 읽음 처리 중 서버 오류가 발생했습니다.');
    }
});

module.exports = router;
