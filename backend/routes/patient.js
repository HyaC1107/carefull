const express = require('express');
const router = express.Router();

const pool = require('../db');
const { verifyToken } = require('../middleware/auth');
const { parseNumericFields, validateRequiredFields } = require('../utils/validators');
const { sendSuccess, sendError } = require('../utils/response');

/**
 * 요청 본문에서 환자 정보 필수값을 검증합니다.
 *
 * 왜 이렇게 두는가:
 * - 기존 API의 필수값 의미는 유지해야 하므로,
 *   patient.js 전용 검증 규칙은 그대로 유지합니다.
 * - 다만 실제 체크는 utils/validators.js의 공통 함수로 위임합니다.
 */
const validatePatientPayload = (body) => {
    const requiredFields = [
        'name',
        'birth_date',
        'gender',
        'phone_number',
        'address',
        'blood_type',
        'height',
        'weight',
        'fingerprint_id',
        'emergency_contact_name',
        'emergency_contact_phone'
    ];

    return validateRequiredFields(body, requiredFields);
};

/**
 * POST /register
 * 로그인한 사용자의 memberId를 기준으로 환자 정보를 등록합니다.
 */
router.post('/register', verifyToken, async (req, res) => {
    const memberId = req.user.memberId;

    const {
        name,
        birth_date,
        gender,
        phone_number,
        address,
        blood_type,
        emergency_contact_name,
        emergency_contact_phone
    } = req.body;

    const validationError = validatePatientPayload(req.body);
    if (validationError) {
        return sendError(res, 400, validationError);
    }

    const numericFields = parseNumericFields(req.body, [
        'height',
        'weight',
        'fingerprint_id'
    ]);

    if (!numericFields) {
        return sendError(res, 400, 'height, weight, fingerprint_id는 숫자여야 합니다.');
    }

    const {
        height: parsedHeight,
        weight: parsedWeight,
        fingerprint_id: parsedFingerprintId
    } = numericFields;

    try {
        const existingUserQuery = `
            SELECT user_id
            FROM users
            WHERE member_id = $1
            LIMIT 1
        `;
        const existingUserResult = await pool.query(existingUserQuery, [memberId]);

        if (existingUserResult.rows.length > 0) {
            return sendError(res, 409, '이미 등록된 환자 정보가 있습니다.');
        }

        const existingFingerprintQuery = `
            SELECT user_id
            FROM users
            WHERE fingerprint_id = $1
            LIMIT 1
        `;
        const existingFingerprintResult = await pool.query(existingFingerprintQuery, [parsedFingerprintId]);

        if (existingFingerprintResult.rows.length > 0) {
            return sendError(res, 409, '이미 사용 중인 fingerprint_id입니다.');
        }

        const insertQuery = `
            INSERT INTO users (
                member_id,
                name,
                birth_date,
                gender,
                phone_number,
                address,
                blood_type,
                height,
                weight,
                fingerprint_id,
                emergency_contact_name,
                emergency_contact_phone
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
            RETURNING
                user_id,
                member_id,
                name,
                birth_date,
                gender,
                phone_number,
                address,
                blood_type,
                height,
                weight,
                fingerprint_id,
                emergency_contact_name,
                emergency_contact_phone,
                created_at,
                updated_at
        `;

        const { rows } = await pool.query(insertQuery, [
            memberId,
            name,
            birth_date,
            gender,
            phone_number,
            address,
            blood_type,
            parsedHeight,
            parsedWeight,
            parsedFingerprintId,
            emergency_contact_name,
            emergency_contact_phone
        ]);

        return sendSuccess(res, 201, {
            message: '환자 정보가 등록되었습니다.',
            patient: rows[0]
        });
    } catch (error) {
        console.error('환자 등록 중 오류가 발생했습니다:', error);
        return sendError(res, 500, '환자 등록 중 서버 오류가 발생했습니다.');
    }
});

/**
 * GET /me
 * 로그인한 사용자의 memberId 기준으로 내 환자 정보를 조회합니다.
 */
router.get('/me', verifyToken, async (req, res) => {
    const memberId = req.user.memberId;

    try {
        const selectQuery = `
            SELECT
                user_id,
                member_id,
                name,
                birth_date,
                gender,
                phone_number,
                address,
                blood_type,
                height,
                weight,
                fingerprint_id,
                emergency_contact_name,
                emergency_contact_phone,
                created_at,
                updated_at
            FROM users
            WHERE member_id = $1
            LIMIT 1
        `;

        const { rows } = await pool.query(selectQuery, [memberId]);

        if (rows.length === 0) {
            return sendError(res, 404, '등록된 환자 정보가 없습니다.');
        }

        return sendSuccess(res, 200, {
            patient: rows[0]
        });
    } catch (error) {
        console.error('환자 정보 조회 중 오류가 발생했습니다:', error);
        return sendError(res, 500, '환자 정보 조회 중 서버 오류가 발생했습니다.');
    }
});

/**
 * PUT /me
 * 로그인한 사용자의 memberId 기준으로 내 환자 정보를 수정합니다.
 */
router.put('/me', verifyToken, async (req, res) => {
    const memberId = req.user.memberId;

    const {
        name,
        birth_date,
        gender,
        phone_number,
        address,
        blood_type,
        emergency_contact_name,
        emergency_contact_phone
    } = req.body;

    const validationError = validatePatientPayload(req.body);
    if (validationError) {
        return sendError(res, 400, validationError);
    }

    const numericFields = parseNumericFields(req.body, [
        'height',
        'weight',
        'fingerprint_id'
    ]);

    if (!numericFields) {
        return sendError(res, 400, 'height, weight, fingerprint_id는 숫자여야 합니다.');
    }

    const {
        height: parsedHeight,
        weight: parsedWeight,
        fingerprint_id: parsedFingerprintId
    } = numericFields;

    try {
        const fingerprintCheckQuery = `
            SELECT user_id
            FROM users
            WHERE fingerprint_id = $1
              AND member_id <> $2
            LIMIT 1
        `;
        const fingerprintCheckResult = await pool.query(fingerprintCheckQuery, [
            parsedFingerprintId,
            memberId
        ]);

        if (fingerprintCheckResult.rows.length > 0) {
            return sendError(res, 409, '이미 사용 중인 fingerprint_id입니다.');
        }

        const updateQuery = `
            UPDATE users
            SET
                name = $1,
                birth_date = $2,
                gender = $3,
                phone_number = $4,
                address = $5,
                blood_type = $6,
                height = $7,
                weight = $8,
                fingerprint_id = $9,
                emergency_contact_name = $10,
                emergency_contact_phone = $11,
                updated_at = CURRENT_TIMESTAMP
            WHERE member_id = $12
            RETURNING
                user_id,
                member_id,
                name,
                birth_date,
                gender,
                phone_number,
                address,
                blood_type,
                height,
                weight,
                fingerprint_id,
                emergency_contact_name,
                emergency_contact_phone,
                created_at,
                updated_at
        `;

        const { rows } = await pool.query(updateQuery, [
            name,
            birth_date,
            gender,
            phone_number,
            address,
            blood_type,
            parsedHeight,
            parsedWeight,
            parsedFingerprintId,
            emergency_contact_name,
            emergency_contact_phone,
            memberId
        ]);

        if (rows.length === 0) {
            return sendError(res, 404, '수정할 환자 정보가 없습니다.');
        }

        return sendSuccess(res, 200, {
            message: '환자 정보가 수정되었습니다.',
            patient: rows[0]
        });
    } catch (error) {
        console.error('환자 정보 수정 중 오류가 발생했습니다:', error);
        return sendError(res, 500, '환자 정보 수정 중 서버 오류가 발생했습니다.');
    }
});

module.exports = router;
