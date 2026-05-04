const express = require('express');
const router = express.Router();

const pool = require('../db');
const { verifyToken } = require('../middleware/auth');
const { find_patient_id_by_mem_id } = require('../utils/auth-user');
const { parseNumericFields, parseNumericValue, validateRequiredFields } = require('../utils/validators');
const { sendSuccess, sendError } = require('../utils/response');
const { send_schedule_created_push_safe } = require('../services/push.service');
const { getKstWallClockDate } = require('../utils/dashboard-helpers');

const validate_schedule_payload = (body) => {
    const required_fields = [
        'start_date',
        'status'
    ];

    const validation_error = validateRequiredFields(body, required_fields);
    if (validation_error) {
        return validation_error;
    }

    if (body.time_to_take_list !== undefined) {
        if (!Array.isArray(body.time_to_take_list)) {
            return 'time_to_take_list must be an array.';
        }

        if (body.time_to_take_list.length === 0) {
            return 'time_to_take_list must not be empty.';
        }
    } else {
        const time_validation_error = validateRequiredFields(body, ['time_to_take']);
        if (time_validation_error) {
            return time_validation_error;
        }
    }

    if (Array.isArray(body.medications) && body.medications.length > 0) {
        return null;
    }

    return validateRequiredFields(body, ['medi_id']);
};

const parse_schedule_medi_ids = (body) => {
    if (Array.isArray(body.medications) && body.medications.length > 0) {
        const medi_ids = [];

        for (const medication of body.medications) {
            const raw_medi_id =
                typeof medication === 'object' && medication !== null
                    ? medication.medi_id
                    : medication;
            const parsed_medi_id = parseNumericValue(raw_medi_id);

            if (parsed_medi_id === null) {
                return null;
            }

            if (!medi_ids.includes(parsed_medi_id)) {
                medi_ids.push(parsed_medi_id);
            }
        }

        return medi_ids;
    }

    const parsed_medi_id = parseNumericValue(body.medi_id);
    return parsed_medi_id === null ? null : [parsed_medi_id];
};

const parse_schedule_dose_interval = (value) => {
    if (value === undefined || value === null || value === '') {
        return null;
    }

    const parsed_dose_interval = parseNumericValue(value);

    if (
        parsed_dose_interval === null ||
        !Number.isInteger(parsed_dose_interval) ||
        parsed_dose_interval < 1 ||
        parsed_dose_interval > 5
    ) {
        return undefined;
    }

    return parsed_dose_interval;
};

const parse_schedule_times = (body) => {
    const raw_times =
        body.time_to_take_list !== undefined
            ? body.time_to_take_list
            : [body.time_to_take];
    const parsed_times = [];

    for (const raw_time of raw_times) {
        const parsed_time = String(raw_time || '').trim();

        if (!parsed_time) {
            return null;
        }

        if (!parsed_times.includes(parsed_time)) {
            parsed_times.push(parsed_time);
        }
    }

    return parsed_times.length > 0 ? parsed_times : null;
};

const parse_date_only = (value) => {
    if (!value) {
        return null;
    }

    const [year, month, day] = String(value).slice(0, 10).split('-').map(Number);

    if (![year, month, day].every(Number.isInteger)) {
        return null;
    }

    return new Date(year, month - 1, day);
};

const format_date_only = (date) => {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');

    return `${year}-${month}-${day}`;
};

const add_days = (date, days) => {
    const next_date = new Date(date);
    next_date.setDate(next_date.getDate() + days);

    return next_date;
};

const build_schedule_datetime = (date, time_to_take) => {
    const [hours = 0, minutes = 0, seconds = 0] = String(time_to_take)
        .split(':')
        .map(Number);

    if (![hours, minutes, seconds].every(Number.isFinite)) {
        return null;
    }

    const schedule_datetime = new Date(date);
    schedule_datetime.setHours(hours, minutes, seconds || 0, 0);

    return schedule_datetime;
};

const resolve_insert_start_date = (start_date, end_date, time_to_take, registered_at) => {
    const start_date_only = parse_date_only(start_date);

    if (!start_date_only) {
        return null;
    }

    const schedule_datetime = build_schedule_datetime(start_date_only, time_to_take);

    if (!schedule_datetime) {
        return null;
    }

    if (schedule_datetime.getTime() >= registered_at.getTime()) {
        return format_date_only(start_date_only);
    }

    const next_date = add_days(start_date_only, 1);
    const end_date_only = end_date ? parse_date_only(end_date) : null;

    if (end_date_only && next_date.getTime() > end_date_only.getTime()) {
        return null;
    }

    return format_date_only(next_date);
};

const to_schedule_response = (row) => ({
    sche_id: row.sche_id,
    patient_id: row.patient_id,
    medi_id: row.medi_id,
    medi_name: row.medi_name ?? null,
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
        start_date,
        end_date,
        dose_interval,
        status
    } = req.body;

    const parsed_medi_ids = parse_schedule_medi_ids(req.body);

    if (!parsed_medi_ids) {
        return sendError(res, 400, 'medi_id must be numeric.');
    }

    const parsed_times = parse_schedule_times(req.body);

    if (!parsed_times) {
        return sendError(res, 400, 'time_to_take is required.');
    }

    const parsed_dose_interval = parse_schedule_dose_interval(dose_interval);

    if (parsed_dose_interval === undefined) {
        return sendError(res, 400, 'dose_interval must be an integer from 1 to 5.');
    }

    const registered_at = getKstWallClockDate();
    registered_at.setSeconds(0, 0);

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

        const client = await pool.connect();

        try {
            await client.query('BEGIN');

            const created_rows = [];

            for (const parsed_medi_id of parsed_medi_ids) {
                for (const parsed_time of parsed_times) {
                    const insert_start_date = resolve_insert_start_date(
                        start_date,
                        end_date,
                        parsed_time,
                        registered_at
                    );

                    if (!insert_start_date) {
                        continue;
                    }

                    const { rows } = await client.query(insert_query, [
                        patient_id,
                        parsed_medi_id,
                        parsed_time,
                        insert_start_date,
                        end_date,
                        parsed_dose_interval,
                        status
                    ]);

                    created_rows.push(rows[0]);
                }
            }

            if (created_rows.length === 0) {
                await client.query('ROLLBACK');
                return sendError(res, 400, 'No valid future schedule time to create.');
            }

            await client.query('COMMIT');
            await send_schedule_created_push_safe(mem_id);

            return sendSuccess(res, 201, {
                message: 'Schedule created successfully.',
                schedule: to_schedule_response(created_rows[0]),
                schedules: created_rows.map(to_schedule_response)
            });
        } catch (error) {
            await client.query('ROLLBACK');
            throw error;
        } finally {
            client.release();
        }
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
                s.sche_id,
                s.patient_id,
                s.medi_id,
                m.medi_name,
                s.time_to_take,
                s.start_date,
                s.end_date,
                s.dose_interval,
                s.status
            FROM schedules s
            LEFT JOIN medications m ON m.medi_id = s.medi_id
            WHERE s.patient_id = $1
            ORDER BY s.start_date, s.time_to_take, s.sche_id
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
    const parsed_dose_interval = parse_schedule_dose_interval(dose_interval);

    if (parsed_dose_interval === undefined) {
        return sendError(res, 400, 'dose_interval must be an integer from 1 to 5.');
    }

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
            parsed_dose_interval,
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

// GET /api/schedule/device  — JWT 불필요, device_uid 로 인증
router.get('/device', async (req, res) => {
    const { device_uid } = req.query;

    if (!device_uid || !String(device_uid).trim()) {
        return sendError(res, 400, 'device_uid is required.');
    }

    try {
        const query = `
            SELECT
                s.sche_id,
                s.patient_id,
                s.medi_id,
                s.time_to_take,
                s.start_date,
                s.end_date,
                s.dose_interval,
                s.status,
                m.medi_name
            FROM schedules s
            INNER JOIN devices d ON d.patient_id = s.patient_id
            LEFT JOIN medications m ON m.medi_id = s.medi_id
            WHERE d.device_uid = $1
              AND s.status = 'ACTIVE'
              AND s.start_date <= (CURRENT_TIMESTAMP AT TIME ZONE 'Asia/Seoul')::date
              AND (
                  s.end_date IS NULL
                  OR s.end_date >= (CURRENT_TIMESTAMP AT TIME ZONE 'Asia/Seoul')::date
              )
              AND (
                  (CURRENT_TIMESTAMP AT TIME ZONE 'Asia/Seoul')::date > (s.created_at AT TIME ZONE 'Asia/Seoul')::date
                  OR (
                      (CURRENT_TIMESTAMP AT TIME ZONE 'Asia/Seoul')::date = (s.created_at AT TIME ZONE 'Asia/Seoul')::date
                      AND ((CURRENT_TIMESTAMP AT TIME ZONE 'Asia/Seoul')::date + s.time_to_take) >= (s.created_at AT TIME ZONE 'Asia/Seoul')
                  )
              )
            ORDER BY s.time_to_take, s.sche_id
        `;

        const { rows } = await pool.query(query, [String(device_uid).trim()]);

        return sendSuccess(res, 200, {
            schedules: rows.map(row => ({
                sche_id:       row.sche_id,
                patient_id:    row.patient_id,
                medi_id:       row.medi_id,
                time_to_take:  row.time_to_take,
                start_date:    row.start_date,
                end_date:      row.end_date,
                dose_interval: row.dose_interval,
                status:        row.status,
                medi_name:     row.medi_name,
            }))
        });
    } catch (error) {
        console.error('Device schedule fetch error:', error);
        return sendError(res, 500, 'Server error while fetching device schedules.');
    }
});

module.exports = router;
