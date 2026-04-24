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
        console.error('??紐⑸줉 議고쉶 以??ㅻ쪟媛 諛쒖깮?덉뒿?덈떎:', error);

        return res.status(500).json({
            success: false,
            message: '??紐⑸줉 議고쉶 以??쒕쾭 ?ㅻ쪟媛 諛쒖깮?덉뒿?덈떎.'
        });
    }
});

router.get('/search', async (req, res) => {
    const keyword = (req.query.keyword || '').trim();

    if (!keyword) {
        return res.status(400).json({
            success: false,
            message: 'keyword 荑쇰━ ?뚮씪誘명꽣???꾩닔?낅땲??'
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
        `;

        const { rows } = await pool.query(query, [`%${keyword}%`]);

        return res.status(200).json({
            success: true,
            data: rows
        });
    } catch (error) {
        console.error('??寃??以??ㅻ쪟媛 諛쒖깮?덉뒿?덈떎:', error);

        return res.status(500).json({
            success: false,
            message: '??寃??以??쒕쾭 ?ㅻ쪟媛 諛쒖깮?덉뒿?덈떎.'
        });
    }
});

module.exports = router;
