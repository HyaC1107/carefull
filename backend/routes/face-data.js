// routes/face-data.js
const express = require('express');
const router = express.Router();

const pool = require('../db');
const { verifyToken } = require('../middleware/auth');
const { findUserIdByMemberId } = require('../utils/auth-user');
const { sendSuccess, sendError } = require('../utils/response');
const { validateRequiredFields } = require('../utils/validators');

/**
 * 얼굴 임베딩 저장 요청 body를 검증합니다.
 */
const validateFaceDataPayload = (body) => {
    const requiredFields = ['embedding'];
    return validateRequiredFields(body, requiredFields);
};

/**
 * embedding 배열을 DB 저장용 값으로 정리합니다.
 *
 * 현재 전제:
 * - PostgreSQL face_data.embedding 컬럼은 VECTOR(128)
 * - pgvector 사용 시 '[0.1, 0.2, ...]' 형태 문자열로 전달 가능
 *
 * 참고:
 * - 드라이버/pgvector 설정에 따라 배열 자체 전달이 가능할 수도 있으나,
 *   현재 프로젝트에서는 우선 안전하게 문자열로 변환하는 뼈대 코드로 둡니다.
 */
const normalizeEmbeddingValue = (embedding) => {
    if (!Array.isArray(embedding)) {
        return null;
    }

    if (embedding.length === 0) {
        return null;
    }

    const parsedEmbedding = [];

    for (const value of embedding) {
        const parsedValue = Number(value);

        if (Number.isNaN(parsedValue)) {
            return null;
        }

        parsedEmbedding.push(parsedValue);
    }

    return `[${parsedEmbedding.join(',')}]`;
};

/**
 * POST /api/face-data
 * 로그인한 사용자 기준 user_id를 찾아 얼굴 임베딩을 저장합니다.
 */
router.post('/', verifyToken, async (req, res) => {
    const memberId = req.user.memberId;

    const validationError = validateFaceDataPayload(req.body);
    if (validationError) {
        return sendError(res, 400, validationError);
    }

    const { embedding } = req.body;
    const normalizedEmbedding = normalizeEmbeddingValue(embedding);

    if (!normalizedEmbedding) {
        return sendError(res, 400, 'embedding은 숫자 배열이어야 합니다.');
    }

    try {
        const userId = await findUserIdByMemberId(memberId);

        if (!userId) {
            return sendError(res, 404, '등록된 사용자 정보가 없습니다.');
        }

        const insertQuery = `
            INSERT INTO face_data (
                user_id,
                embedding
            )
            VALUES ($1, $2)
            RETURNING
                face_id,
                user_id,
                embedding,
                created_at
        `;

        const { rows } = await pool.query(insertQuery, [
            userId,
            normalizedEmbedding
        ]);

        return sendSuccess(res, 201, {
            message: '얼굴 데이터가 저장되었습니다.',
            face_data: rows[0]
        });
    } catch (error) {
        console.error('얼굴 데이터 저장 중 오류가 발생했습니다:', error);
        return sendError(res, 500, '얼굴 데이터 저장 중 서버 오류가 발생했습니다.');
    }
});

/**
 * GET /api/face-data
 * 로그인한 사용자 기준 얼굴 데이터 목록을 최신순으로 조회합니다.
 */
router.get('/', verifyToken, async (req, res) => {
    const memberId = req.user.memberId;

    try {
        const userId = await findUserIdByMemberId(memberId);

        if (!userId) {
            return sendError(res, 404, '등록된 사용자 정보가 없습니다.');
        }

        const query = `
            SELECT
                face_id,
                user_id,
                embedding,
                created_at
            FROM face_data
            WHERE user_id = $1
            ORDER BY created_at DESC, face_id DESC
        `;

        const { rows } = await pool.query(query, [userId]);

        return sendSuccess(res, 200, {
            face_data: rows
        });
    } catch (error) {
        console.error('얼굴 데이터 조회 중 오류가 발생했습니다:', error);
        return sendError(res, 500, '얼굴 데이터 조회 중 서버 오류가 발생했습니다.');
    }
});

module.exports = router;
