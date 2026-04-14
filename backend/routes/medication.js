const express = require('express');
const router = express.Router();

const pool = require('../db');

/**
 * GET /api/medication
 * 공통 약 사전 테이블인 medications의 전체 목록을 조회합니다.
 *
 * 응답 컬럼:
 * - medication_id
 * - item_seq
 * - name
 */
router.get('/', async (req, res) => {
    try {
        const query = `
            SELECT
                medication_id,
                item_seq,
                name
            FROM medications
            ORDER BY name, medication_id
        `;

        const { rows } = await pool.query(query);

        return res.status(200).json({
            success: true,
            data: rows
        });
    } catch (error) {
        console.error('약 목록 조회 중 오류가 발생했습니다:', error);

        return res.status(500).json({
            success: false,
            message: '약 목록 조회 중 서버 오류가 발생했습니다.'
        });
    }
});

/**
 * GET /api/medication/search?keyword=...
 * 공통 약 사전 테이블에서 약 이름(name) 기준 부분 검색을 수행합니다.
 */
router.get('/search', async (req, res) => {
    const keyword = (req.query.keyword || '').trim();

    if (!keyword) {
        return res.status(400).json({
            success: false,
            message: 'keyword 쿼리 파라미터는 필수입니다.'
        });
    }

    try {
        const query = `
            SELECT
                medication_id,
                item_seq,
                name
            FROM medications
            WHERE name ILIKE $1
            ORDER BY name, medication_id
        `;

        const { rows } = await pool.query(query, [`%${keyword}%`]);

        return res.status(200).json({
            success: true,
            data: rows
        });
    } catch (error) {
        console.error('약 검색 중 오류가 발생했습니다:', error);

        return res.status(500).json({
            success: false,
            message: '약 검색 중 서버 오류가 발생했습니다.'
        });
    }
});

module.exports = router;
