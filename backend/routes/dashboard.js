const express = require('express');
const router = express.Router();

const { verifyToken } = require('../middleware/auth');
const { sendSuccess, sendError } = require('../utils/response');
const { get_dashboard_data_by_mem_id } = require('../services/dashboard.service');

router.get('/', verifyToken, async (req, res) => {
    const mem_id = req.user.mem_id;

    try {
        const dashboard_data = await get_dashboard_data_by_mem_id(mem_id);

        if (!dashboard_data) {
            return sendError(res, 404, 'Patient not found.');
        }

        return sendSuccess(res, 200, {
            message: 'Dashboard fetched successfully.',
            data: dashboard_data
        });
    } catch (error) {
        console.error('Dashboard fetch error:', error);
        return sendError(res, 500, 'Server error while fetching dashboard.');
    }
});

module.exports = router;
