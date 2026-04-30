const express = require('express');
const multer = require('multer');

const router = express.Router();

const pool = require('../db');
const { verifyToken } = require('../middleware/auth');
const { find_patient_id_by_mem_id } = require('../utils/auth-user');
const { sendSuccess, sendError } = require('../utils/response');
const { getKstWallClockDate } = require('../utils/dashboard-helpers');
const {
    call_gemini,
    normalize_prescription_payload,
    validate_prescription_confirm
} = require('../services/prescription-ai.service');
const { send_schedule_created_push_safe } = require('../services/push.service');

const upload = multer({
    storage: multer.memoryStorage(),
    limits: {
        fileSize: 5 * 1024 * 1024
    },
    fileFilter: (req, file, callback) => {
        if (!String(file.mimetype || '').startsWith('image/')) {
            return callback(new Error('Prescription file must be an image.'));
        }

        return callback(null, true);
    }
});

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

const ensure_time_seconds = (time) => (
    String(time).length === 5 ? `${time}:00` : String(time)
);

const find_or_create_medication = async (client, medicine_name) => {
    const normalized_name = String(medicine_name || '').trim();
    const existing_result = await client.query(
        `
            SELECT medi_id, medi_name
            FROM medications
            WHERE LOWER(medi_name) = LOWER($1)
            ORDER BY medi_id
            LIMIT 1
        `,
        [normalized_name]
    );

    if (existing_result.rows.length > 0) {
        return existing_result.rows[0];
    }

    const insert_result = await client.query(
        `
            INSERT INTO medications (medi_name)
            VALUES ($1)
            RETURNING medi_id, medi_name
        `,
        [normalized_name]
    );

    return insert_result.rows[0];
};

router.post('/preview', verifyToken, upload.single('prescription'), async (req, res) => {
    if (!req.file) {
        return sendError(res, 400, 'Prescription image is required.');
    }

    try {
        const analysis = await call_gemini({
            image_buffer: req.file.buffer,
            mime_type: req.file.mimetype
        });
        const data = normalize_prescription_payload(analysis);

        return sendSuccess(res, 200, { data });
    } catch (error) {
        console.error('Prescription preview error:', error.response?.data || error);
        return sendError(res, 500, 'Server error while analyzing prescription.');
    }
});

router.post('/confirm', verifyToken, async (req, res) => {
    const mem_id = req.user.mem_id;
    const { normalized, errors } = validate_prescription_confirm(req.body);

    if (errors.length > 0) {
        return sendError(res, 400, 'Prescription schedule validation failed.', {
            errors,
            data: normalized
        });
    }

    const registered_at = getKstWallClockDate();
    registered_at.setSeconds(0, 0);

    const client = await pool.connect();

    try {
        const patient_id = await find_patient_id_by_mem_id(mem_id);

        if (!patient_id) {
            return sendError(res, 404, 'Patient not found.');
        }

        await client.query('BEGIN');

        const created_rows = [];

        for (const medication of normalized.medications) {
            const medication_row = await find_or_create_medication(
                client,
                medication.medicine_name
            );

            for (const time of medication.times) {
                const time_to_take = ensure_time_seconds(time);
                const insert_start_date = resolve_insert_start_date(
                    medication.start_date,
                    medication.end_date,
                    time_to_take,
                    registered_at
                );

                if (!insert_start_date) {
                    continue;
                }

                const { rows } = await client.query(
                    `
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
                    `,
                    [
                        patient_id,
                        medication_row.medi_id,
                        time_to_take,
                        insert_start_date,
                        medication.end_date,
                        null,
                        'ACTIVE'
                    ]
                );

                created_rows.push({
                    ...rows[0],
                    medi_name: medication_row.medi_name
                });
            }
        }

        if (created_rows.length === 0) {
            await client.query('ROLLBACK');
            return sendError(res, 400, 'No valid future schedule time to create.');
        }

        await client.query('COMMIT');
        await send_schedule_created_push_safe(mem_id);

        return sendSuccess(res, 201, {
            message: 'Prescription schedules created successfully.',
            schedules: created_rows.map(to_schedule_response)
        });
    } catch (error) {
        await client.query('ROLLBACK');
        console.error('Prescription confirm error:', error);
        return sendError(res, 500, 'Server error while creating prescription schedules.');
    } finally {
        client.release();
    }
});

module.exports = router;
