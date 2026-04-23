const express = require('express');
const router = express.Router();

const pool = require('../db');

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

        return res.status(200).json({
            success: true,
            data: rows
        });
    } catch (error) {
        console.error('Medication list fetch error:', error);

        return res.status(500).json({
            success: false,
            message: 'Server error while fetching medications.'
        });
    }
});

router.get('/search', async (req, res) => {
    const keyword = (req.query.keyword || '').trim();

    if (!keyword) {
        return res.status(400).json({
            success: false,
            message: 'keyword query parameter is required.'
        });
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
            LIMIT 10
        `;

        const { rows } = await pool.query(query, [`%${keyword}%`]);

        return res.status(200).json({
            success: true,
            data: rows
        });
    } catch (error) {
        console.error('Medication search error:', error);

        return res.status(500).json({
            success: false,
            message: 'Server error while searching medications.'
        });
    }
});

module.exports = router;
