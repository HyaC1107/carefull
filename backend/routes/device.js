const express = require('express');                 // Express 라우터 사용
const router = express.Router();

const pool = require('../db');                      // PostgreSQL pool
const { verifyToken } = require('../middleware/auth'); // JWT 검증 미들웨어

/**
 * [공통 함수]
 * 로그인한 memberId로 users 테이블의 user_id를 찾는다.
 * device 등록은 users.user_id와 연결해야 하므로 먼저 환자 등록이 되어 있어야 한다.
 */
const findUserIdByMemberId = async (memberId) => {
    const query = `
        SELECT user_id
        FROM users
        WHERE member_id = $1
        LIMIT 1
    `;

    const { rows } = await pool.query(query, [memberId]);
    return rows.length > 0 ? rows[0].user_id : null;
};

/**
 * POST /register
 * 로그인한 사용자의 환자 정보(user_id)에
 * 입력한 serial_number 기기를 연결한다.
 *
 * 요청 body 예시:
 * {
 *   "serial_number": "CAREFULL-0003"
 * }
 */
router.post('/register', verifyToken, async (req, res) => {
    const memberId = req.user.memberId;             // auth.js 기준 통일된 사용자 식별자
    const { serial_number } = req.body;

    if (!serial_number) {
        return res.status(400).json({
            success: false,
            message: 'serial_number는 필수입니다.'
        });
    }

    try {
        // 1. 현재 로그인한 memberId에 연결된 환자(user)가 있는지 확인
        const userId = await findUserIdByMemberId(memberId);

        if (!userId) {
            return res.status(404).json({
                success: false,
                message: '먼저 환자 정보를 등록해야 기기를 연결할 수 있습니다.'
            });
        }

        // 2. 입력한 시리얼 번호가 실제 devices 테이블에 존재하는지 확인
        const findDeviceQuery = `
            SELECT device_id, serial_number, user_id, status, registered_at
            FROM devices
            WHERE serial_number = $1
            LIMIT 1
        `;
        const deviceResult = await pool.query(findDeviceQuery, [serial_number]);

        if (deviceResult.rows.length === 0) {
            return res.status(404).json({
                success: false,
                message: '존재하지 않는 시리얼 번호입니다.'
            });
        }

        const device = deviceResult.rows[0];

        // 3. 이미 다른 사용자에게 등록된 기기인지 확인
        if (device.user_id && device.user_id !== userId) {
            return res.status(409).json({
                success: false,
                message: '이미 다른 사용자에게 등록된 기기입니다.'
            });
        }

        // 4. 이미 내 계정에 연결된 기기인지 확인
        if (device.user_id === userId) {
            return res.status(200).json({
                success: true,
                message: '이미 내 계정에 등록된 기기입니다.',
                device
            });
        }

        // 5. 현재 사용자가 이미 다른 기기를 등록했는지 확인
        // devices.user_id가 UNIQUE 구조라면 한 사용자당 한 기기만 연결 가능하게 보는 게 자연스럽다.
        const existingMyDeviceQuery = `
            SELECT device_id, serial_number
            FROM devices
            WHERE user_id = $1
            LIMIT 1
        `;
        const existingMyDeviceResult = await pool.query(existingMyDeviceQuery, [userId]);

        if (existingMyDeviceResult.rows.length > 0) {
            return res.status(409).json({
                success: false,
                message: '이미 등록된 기기가 있습니다. 기존 기기 해제 후 다시 시도해주세요.',
                device: existingMyDeviceResult.rows[0]
            });
        }

        // 6. 기기 등록 처리
        const updateQuery = `
            UPDATE devices
            SET
                user_id = $1,
                status = 'REGISTERED',
                registered_at = CURRENT_TIMESTAMP
            WHERE serial_number = $2
            RETURNING
                device_id,
                serial_number,
                user_id,
                status,
                last_ping,
                registered_at,
                created_at
        `;

        const { rows } = await pool.query(updateQuery, [userId, serial_number]);

        return res.status(200).json({
            success: true,
            message: '기기 등록이 완료되었습니다.',
            device: rows[0]
        });
    } catch (error) {
        console.error('기기 등록 중 오류가 발생했습니다:', error);

        return res.status(500).json({
            success: false,
            message: '기기 등록 중 서버 오류가 발생했습니다.'
        });
    }
});

/**
 * GET /me
 * 로그인한 사용자의 현재 등록 기기 조회
 */
router.get('/me', verifyToken, async (req, res) => {
    const memberId = req.user.memberId;

    try {
        // 1. 로그인한 memberId 기준으로 user_id 찾기
        const userId = await findUserIdByMemberId(memberId);

        if (!userId) {
            return res.status(404).json({
                success: false,
                message: '등록된 환자 정보가 없습니다.'
            });
        }

        // 2. 현재 사용자에게 연결된 기기 조회
        const query = `
            SELECT
                device_id,
                serial_number,
                user_id,
                status,
                last_ping,
                registered_at,
                created_at
            FROM devices
            WHERE user_id = $1
            LIMIT 1
        `;

        const { rows } = await pool.query(query, [userId]);

        if (rows.length === 0) {
            return res.status(404).json({
                success: false,
                message: '등록된 기기 정보가 없습니다.'
            });
        }

        return res.status(200).json({
            success: true,
            device: rows[0]
        });
    } catch (error) {
        console.error('내 기기 조회 중 오류가 발생했습니다:', error);

        return res.status(500).json({
            success: false,
            message: '기기 조회 중 서버 오류가 발생했습니다.'
        });
    }
});

/**
 * DELETE /me
 * 로그인한 사용자의 현재 등록 기기 해제
 * 필요하면 나중에 붙이면 되고, 지금 바로 써도 된다.
 */
router.delete('/me', verifyToken, async (req, res) => {
    const memberId = req.user.memberId;

    try {
        // 1. user_id 조회
        const userId = await findUserIdByMemberId(memberId);

        if (!userId) {
            return res.status(404).json({
                success: false,
                message: '등록된 환자 정보가 없습니다.'
            });
        }

        // 2. 연결된 기기 해제
        const updateQuery = `
            UPDATE devices
            SET
                user_id = NULL,
                status = 'UNREGISTERED',
                registered_at = NULL
            WHERE user_id = $1
            RETURNING
                device_id,
                serial_number,
                user_id,
                status,
                last_ping,
                registered_at,
                created_at
        `;

        const { rows } = await pool.query(updateQuery, [userId]);

        if (rows.length === 0) {
            return res.status(404).json({
                success: false,
                message: '해제할 기기 정보가 없습니다.'
            });
        }

        return res.status(200).json({
            success: true,
            message: '기기 연결이 해제되었습니다.',
            device: rows[0]
        });
    } catch (error) {
        console.error('기기 해제 중 오류가 발생했습니다:', error);

        return res.status(500).json({
            success: false,
            message: '기기 해제 중 서버 오류가 발생했습니다.'
        });
    }
});

module.exports = router;