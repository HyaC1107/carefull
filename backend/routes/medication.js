const express = require('express');
const router = express.Router();

const pool = require('../db');
const { sendSuccess, sendError } = require('../utils/response');

const DEFAULT_SEARCH_LIMIT = 20;
const MAX_SEARCH_LIMIT = 50;

router.get('/', async (req, res) => {
    try {
        const query = `
            SELECT
                medi_id,
                item_seq,
                medi_name
            FROM medications
            ORDER BY medi_name, medi_id
        `;

        const { rows } = await pool.query(query);

        return sendSuccess(res, 200, {
            message: 'Medications fetched successfully.',
            data: rows
        });
    } catch (error) {
        console.error('Medication list fetch error:', error);

        return sendError(res, 500, 'Failed to fetch medications.');
    }
});

router.get('/search', async (req, res) => {
    const keyword = (req.query.keyword || '').trim();
    const parsed_limit = Number(req.query.limit);
    const limit = Number.isSafeInteger(parsed_limit) && parsed_limit > 0
        ? Math.min(parsed_limit, MAX_SEARCH_LIMIT)
        : DEFAULT_SEARCH_LIMIT;

    if (!keyword) {
        return sendError(res, 400, 'keyword is required.');
    }

    try {
        const query = `
            SELECT
                medi_id,
                item_seq,
                medi_name
            FROM medications
            WHERE medi_name ILIKE $1
            ORDER BY medi_name, medi_id
            LIMIT $2
        `;

        const { rows } = await pool.query(query, [`%${keyword}%`, limit]);

        return sendSuccess(res, 200, {
            message: 'Medication search completed successfully.',
            data: rows
        });
    } catch (error) {
        console.error('Medication search error:', error);

        return sendError(res, 500, 'Failed to search medications.');
    }
});

module.exports = router;
