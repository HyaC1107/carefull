const express = require('express');
const router = express.Router();

const pool = require('../db');
const { verifyToken } = require('../middleware/auth');
const { find_patient_id_by_mem_id } = require('../utils/auth-user');
const { parseNumericFields, parseNumericValue, validateRequiredFields } = require('../utils/validators');
const { sendSuccess, sendError } = require('../utils/response');

const validate_schedule_payload = (body) => {
    const required_fields = [
        'medi_id',
        'time_to_take',
        'start_date',
        'status'
    ];

    return validateRequiredFields(body, required_fields);
};

const to_schedule_response = (row) => ({
    sche_id: row.sche_id,
    patient_id: row.patient_id,
    medi_id: row.medi_id,
    time_to_take: row.time_to_take,
    start_date: row.start_date,
    end_date: row.end_date,
    dose_interval: row.dose_interval,
    status: row.status
});

router.post('/', verifyToken, async (req, res) => {
    const mem_id = req.user.mem_id;

    const validation_error = validate_schedule_payload(req.body);
    if (validation_error) {
        return sendError(res, 400, validation_error);
    }

    const {
        time_to_take,
        start_date,
        end_date,
        dose_interval,
        status
    } = req.body;

    const numeric_fields = parseNumericFields(req.body, ['medi_id']);

    if (!numeric_fields) {
        return sendError(res, 400, 'medi_id must be numeric.');
    }

    const { medi_id: parsed_medi_id } = numeric_fields;

    try {
        const patient_id = await find_patient_id_by_mem_id(mem_id);

        if (!patient_id) {
            return sendError(res, 404, 'Patient not found.');
        }

        const insert_query = `
            INSERT INTO schedules (
                patient_id,
                medi_id,
                time_to_take,
                start_date,
                end_date,
                dose_interval,
                status
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING
                sche_id,
                patient_id,
                medi_id,
                time_to_take,
                start_date,
                end_date,
                dose_interval,
                status
        `;

        const { rows } = await pool.query(insert_query, [
            patient_id,
            parsed_medi_id,
            time_to_take,
            start_date,
            end_date,
            dose_interval ?? null,
            status
        ]);

        return sendSuccess(res, 201, {
            message: 'Schedule created successfully.',
            schedule: to_schedule_response(rows[0])
        });
    } catch (error) {
        console.error('Schedule create error:', error);
        return sendError(res, 500, 'Server error while creating schedule.');
    }
});

router.get('/', verifyToken, async (req, res) => {
    const mem_id = req.user.mem_id;

    try {
        const patient_id = await find_patient_id_by_mem_id(mem_id);

        if (!patient_id) {
            return sendError(res, 404, 'Patient not found.');
        }

        const query = `
            SELECT
                sche_id,
                patient_id,
                medi_id,
                time_to_take,
                start_date,
                end_date,
                dose_interval,
                status
            FROM schedules
            WHERE patient_id = $1
            ORDER BY start_date, time_to_take, sche_id
        `;

        const { rows } = await pool.query(query, [patient_id]);

        return sendSuccess(res, 200, {
            schedules: rows.map(to_schedule_response)
        });
    } catch (error) {
        console.error('Schedule fetch error:', error);
        return sendError(res, 500, 'Server error while fetching schedules.');
    }
});

router.put('/:id', verifyToken, async (req, res) => {
    const mem_id = req.user.mem_id;
    const parsed_sche_id = parseNumericValue(req.params.id);

    if (parsed_sche_id === null) {
        return sendError(res, 400, 'Invalid schedule id.');
    }

    const validation_error = validate_schedule_payload(req.body);
    if (validation_error) {
        return sendError(res, 400, validation_error);
    }

    const {
        time_to_take,
        start_date,
        end_date,
        dose_interval,
        status
    } = req.body;

    const numeric_fields = parseNumericFields(req.body, ['medi_id']);

    if (!numeric_fields) {
        return sendError(res, 400, 'medi_id must be numeric.');
    }

    const { medi_id: parsed_medi_id } = numeric_fields;

    try {
        const patient_id = await find_patient_id_by_mem_id(mem_id);

        if (!patient_id) {
            return sendError(res, 404, 'Patient not found.');
        }

        const update_query = `
            UPDATE schedules
            SET
                medi_id = $1,
                time_to_take = $2,
                start_date = $3,
                end_date = $4,
                dose_interval = $5,
                status = $6,
                updated_at = CURRENT_TIMESTAMP
            WHERE sche_id = $7
              AND patient_id = $8
            RETURNING
                sche_id,
                patient_id,
                medi_id,
                time_to_take,
                start_date,
                end_date,
                dose_interval,
                status
        `;

        const { rows } = await pool.query(update_query, [
            parsed_medi_id,
            time_to_take,
            start_date,
            end_date,
            dose_interval ?? null,
            status,
            parsed_sche_id,
            patient_id
        ]);

        if (rows.length === 0) {
            return sendError(res, 404, 'Schedule not found or access denied.');
        }

        return sendSuccess(res, 200, {
            message: 'Schedule updated successfully.',
            schedule: to_schedule_response(rows[0])
        });
    } catch (error) {
        console.error('Schedule update error:', error);
        return sendError(res, 500, 'Server error while updating schedule.');
    }
});

router.delete('/:id', verifyToken, async (req, res) => {
    const mem_id = req.user.mem_id;
    const parsed_sche_id = parseNumericValue(req.params.id);

    if (parsed_sche_id === null) {
        return sendError(res, 400, 'Invalid schedule id.');
    }

    try {
        const patient_id = await find_patient_id_by_mem_id(mem_id);

        if (!patient_id) {
            return sendError(res, 404, 'Patient not found.');
        }

        const delete_query = `
            DELETE FROM schedules
            WHERE sche_id = $1
              AND patient_id = $2
            RETURNING
                sche_id,
                patient_id,
                medi_id,
                time_to_take,
                start_date,
                end_date,
                dose_interval,
                status
        `;

        const { rows } = await pool.query(delete_query, [parsed_sche_id, patient_id]);

        if (rows.length === 0) {
            return sendError(res, 404, 'Schedule not found or access denied.');
        }

        return sendSuccess(res, 200, {
            message: 'Schedule deleted successfully.',
            schedule: to_schedule_response(rows[0])
        });
    } catch (error) {
        console.error('Schedule delete error:', error);
        return sendError(res, 500, 'Server error while deleting schedule.');
    }
});

module.exports = router;
