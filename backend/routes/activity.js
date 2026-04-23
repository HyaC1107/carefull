const express = require('express');
const router = express.Router();

const pool = require('../db');
const { verifyToken } = require('../middleware/auth');
const { find_patient_id_by_mem_id } = require('../utils/auth-user');
const { sendSuccess, sendError } = require('../utils/response');
const { parseNumericFields, parseNumericValue } = require('../utils/validators');
const {
    ACTIVITY_STATUS,
    DEVICE_EVENT_ACTIVITY_STATUSES,
    decideMedicationStatus
} = require('../utils/activity-status');
const {
    NOTIFICATION_TYPE,
    trigger_activity_notification_safe,
    trigger_low_stock_notification
} = require('../services/notification-trigger.service');
const {
    get_low_stock_snapshot_for_schedule_safe
} = require('../services/stock-calc.service');

const ALLOWED_ACTIVITY_STATUSES = [
    ACTIVITY_STATUS.SUCCESS,
    ACTIVITY_STATUS.FAILED,
    ACTIVITY_STATUS.MISSED,
    ACTIVITY_STATUS.ERROR
];

const to_activity_response = (row) => ({
    activity_id: row.activity_id,
    patient_id: row.patient_id,
    sche_id: row.sche_id,
    sche_time: row.sche_time,
    actual_time: row.actual_time,
    status: row.status,
    is_face_auth: row.is_face_auth,
    is_ai_check: row.is_ai_check,
    similarity_score: row.similarity_score,
    created_at: row.created_at
});

const to_boolean_or_null = (value) => {
    if (value === undefined || value === null || value === '') {
        return null;
    }

    if (typeof value === 'boolean') {
        return value;
    }

    if (typeof value === 'number') {
        if (value === 1) return true;
        if (value === 0) return false;
        return null;
    }

    const normalized_value = String(value).trim().toLowerCase();

    if (['true', '1', 'y', 'yes'].includes(normalized_value)) {
        return true;
    }

    if (['false', '0', 'n', 'no'].includes(normalized_value)) {
        return false;
    }

    return null;
};

const resolve_device_event_payload = (body) => ({
    // Keep both snake_case and camelCase temporarily for device integration.
    device_uid: body.device_uid ?? body.deviceUid ?? null,
    sche_id: body.sche_id ?? body.schedule_id ?? body.scheduleId ?? null,
    event_time: body.event_time ?? body.eventTime ?? null,
    status: body.status ?? null,
    face_verified: body.face_verified ?? body.faceVerified ?? body.is_face_auth ?? null,
    dispensed: body.dispensed ?? null,
    action_verified: body.action_verified ?? body.actionVerified ?? body.is_ai_check ?? null,
    error_code: body.error_code ?? body.errorCode ?? null,
    raw_confidence: body.raw_confidence ?? body.rawConfidence ?? body.similarity_score ?? null
});

const build_schedule_timestamp = (time_to_take, base_date) => {
    const target = new Date(base_date);
    const [hours = 0, minutes = 0, seconds = 0] = String(time_to_take)
        .split(':')
        .map(Number);

    target.setHours(hours, minutes, seconds || 0, 0);
    return target;
};

const insert_activity = async (client, payload) => {
    const insert_query = `
        INSERT INTO activities (
            patient_id,
            sche_id,
            sche_time,
            actual_time,
            status,
            is_face_auth,
            is_ai_check,
            similarity_score
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        RETURNING
            activity_id,
            patient_id,
            sche_id,
            sche_time,
            actual_time,
            status,
            is_face_auth,
            is_ai_check,
            similarity_score,
            created_at
    `;

    const { rows } = await client.query(insert_query, [
        payload.patient_id,
        payload.sche_id,
        payload.sche_time,
        payload.actual_time,
        payload.status,
        payload.is_face_auth,
        payload.is_ai_check,
        payload.similarity_score
    ]);

    return rows[0];
};

const find_duplicate_device_activity = async (client, payload) => {
    // Re-sent device events often reuse the same schedule time and event time.
    const duplicate_query = `
        SELECT
            activity_id,
            patient_id,
            sche_id,
            sche_time,
            actual_time,
            status,
            is_face_auth,
            is_ai_check,
            similarity_score,
            created_at
        FROM activities
        WHERE patient_id = $1
          AND sche_id = $2
          AND sche_time = $3
          AND actual_time = $4
        LIMIT 1
    `;

    const { rows } = await client.query(duplicate_query, [
        payload.patient_id,
        payload.sche_id,
        payload.sche_time,
        payload.actual_time
    ]);

    return rows[0] || null;
};

const touch_device_last_ping_by_patient_id = async (executor, patient_id) => {
    await executor.query(
        `
            UPDATE devices
            SET last_ping = CURRENT_TIMESTAMP
            WHERE patient_id = $1
        `,
        [patient_id]
    );
};

const touch_device_last_ping_by_device_uid = async (executor, device_uid) => {
    await executor.query(
        `
            UPDATE devices
            SET last_ping = CURRENT_TIMESTAMP
            WHERE device_uid = $1
        `,
        [String(device_uid).trim()]
    );
};

router.post('/', verifyToken, async (req, res) => {
    const mem_id = req.user.mem_id;

    const {
        sche_time,
        actual_time,
        status,
        is_face_auth,
        is_ai_check
    } = req.body;

    if (!sche_time) {
        return sendError(res, 400, 'sche_time is required.');
    }

    if (!status || !String(status).trim()) {
        return sendError(res, 400, 'status is required.');
    }

    const numeric_fields = parseNumericFields(req.body, ['sche_id']);
    if (!numeric_fields) {
        return sendError(res, 400, 'sche_id must be numeric.');
    }

    const { sche_id: parsed_sche_id } = numeric_fields;

    let parsed_similarity_score = 0;

    if (
        req.body.similarity_score !== undefined &&
        req.body.similarity_score !== null &&
        req.body.similarity_score !== ''
    ) {
        parsed_similarity_score = parseNumericValue(req.body.similarity_score);

        if (parsed_similarity_score === null) {
            return sendError(res, 400, 'similarity_score must be numeric.');
        }
    }

    const normalized_status = String(status).trim().toUpperCase();

    if (!ALLOWED_ACTIVITY_STATUSES.includes(normalized_status)) {
        return sendError(
            res,
            400,
            `status must be one of ${ALLOWED_ACTIVITY_STATUSES.join(', ')}.`
        );
    }

    const client = await pool.connect();
    let transaction_started = false;

    try {
        const patient_id = await find_patient_id_by_mem_id(mem_id);

        if (!patient_id) {
            return sendError(res, 404, 'Patient not found.');
        }

        const schedule_check_query = `
            SELECT
                sche_id,
                patient_id
            FROM schedules
            WHERE sche_id = $1
              AND patient_id = $2
            LIMIT 1
        `;

        const schedule_check_result = await client.query(schedule_check_query, [
            parsed_sche_id,
            patient_id
        ]);

        if (schedule_check_result.rows.length === 0) {
            return sendError(res, 404, 'Schedule not found or access denied.');
        }

        await client.query('BEGIN');
        transaction_started = true;

        const inserted_activity = await insert_activity(client, {
            patient_id,
            sche_id: parsed_sche_id,
            sche_time,
            actual_time: actual_time || null,
            status: normalized_status,
            is_face_auth: is_face_auth ?? false,
            is_ai_check: is_ai_check ?? false,
            similarity_score: parsed_similarity_score
        });

        await touch_device_last_ping_by_patient_id(client, patient_id);

        const activity = to_activity_response(inserted_activity);

        await client.query('COMMIT');
        transaction_started = false;

        let notification = null;

        if (normalized_status === ACTIVITY_STATUS.SUCCESS) {
            const medication_query = `
                SELECT m.medi_name
                FROM schedules s
                INNER JOIN medications m
                    ON s.medi_id = m.medi_id
                WHERE s.sche_id = $1
                LIMIT 1
            `;

            const medication_result = await pool.query(medication_query, [parsed_sche_id]);
            const notification_result = await trigger_activity_notification_safe({
                mem_id,
                patient_id,
                activity_id: activity.activity_id,
                event_type: NOTIFICATION_TYPE.SUCCESS,
                medi_name: medication_result.rows[0]?.medi_name || 'Registered medication'
            });

            notification = notification_result.notification;

            const low_stock_snapshot = await get_low_stock_snapshot_for_schedule_safe(parsed_sche_id);

            if (low_stock_snapshot.calculable && low_stock_snapshot.should_trigger) {
                await trigger_low_stock_notification({
                    mem_id,
                    patient_id,
                    activity_id: activity.activity_id,
                    medi_name: low_stock_snapshot.base_schedule?.medi_name || medication_result.rows[0]?.medi_name,
                    remaining_quantity: low_stock_snapshot.remaining_quantity
                });
            }
        }

        return sendSuccess(res, 201, {
            message: 'Activity created successfully.',
            activity,
            notification
        });
    } catch (error) {
        if (transaction_started) {
            await client.query('ROLLBACK');
        }
        console.error('Activity create error:', error);
        return sendError(res, 500, 'Server error while creating activity.');
    } finally {
        client.release();
    }
});

router.post('/device-event', async (req, res) => {
    // Device events are validated by device_uid + schedule ownership instead of JWT.
    const resolved_payload = resolve_device_event_payload(req.body);
    const {
        device_uid,
        event_time,
        error_code,
        status
    } = resolved_payload;

    if (!device_uid || !String(device_uid).trim()) {
        return sendError(res, 400, 'device_uid is required.');
    }

    const numeric_fields = parseNumericFields(resolved_payload, ['sche_id']);
    if (!numeric_fields) {
        return sendError(res, 400, 'sche_id must be numeric.');
    }

    const parsed_event_time = event_time ? new Date(event_time) : new Date();
    if (Number.isNaN(parsed_event_time.getTime())) {
        return sendError(res, 400, 'event_time must be a valid datetime string.');
    }

    const parsed_face_verified = to_boolean_or_null(resolved_payload.face_verified);
    const parsed_dispensed = to_boolean_or_null(resolved_payload.dispensed);
    const parsed_action_verified = to_boolean_or_null(resolved_payload.action_verified);
    const normalized_status_from_body = status ? String(status).trim().toUpperCase() : null;
    const has_explicit_status = Boolean(normalized_status_from_body);
    const has_raw_decision_inputs = (
        parsed_face_verified !== null &&
        parsed_dispensed !== null &&
        parsed_action_verified !== null
    );

    // activities.sche_id is NOT NULL in the current schema, so sche_id is required.
    if (!has_explicit_status && !has_raw_decision_inputs && !error_code) {
        return sendError(
            res,
            400,
            'Provide either status, error_code, or all of face_verified/dispensed/action_verified.'
        );
    }

    if (!has_explicit_status && parsed_face_verified === null) {
        return sendError(res, 400, 'face_verified must be boolean.');
    }

    if (!has_explicit_status && parsed_dispensed === null) {
        return sendError(res, 400, 'dispensed must be boolean.');
    }

    if (!has_explicit_status && parsed_action_verified === null) {
        return sendError(res, 400, 'action_verified must be boolean.');
    }

    if (
        has_explicit_status &&
        !DEVICE_EVENT_ACTIVITY_STATUSES.includes(normalized_status_from_body)
    ) {
        return sendError(
            res,
            400,
            `status must be one of ${DEVICE_EVENT_ACTIVITY_STATUSES.join(', ')}.`
        );
    }

    let parsed_similarity_score = 0;

    if (
        resolved_payload.raw_confidence !== undefined &&
        resolved_payload.raw_confidence !== null &&
        resolved_payload.raw_confidence !== ''
    ) {
        parsed_similarity_score = parseNumericValue(resolved_payload.raw_confidence);

        if (parsed_similarity_score === null) {
            return sendError(res, 400, 'raw_confidence must be numeric.');
        }
    }

    const normalized_status = decideMedicationStatus({
        face_verified: parsed_face_verified,
        dispensed: parsed_dispensed,
        action_verified: parsed_action_verified,
        error_code,
        status: normalized_status_from_body
    });

    if (!DEVICE_EVENT_ACTIVITY_STATUSES.includes(normalized_status)) {
        return sendError(res, 500, 'Unable to determine final activity status.');
    }

    const client = await pool.connect();
    let transaction_started = false;

    try {
        const schedule_query = `
            SELECT
                s.sche_id,
                s.patient_id,
                s.time_to_take,
                m.medi_name,
                p.mem_id,
                d.device_uid
            FROM schedules s
            INNER JOIN patients p
                ON s.patient_id = p.patient_id
            INNER JOIN devices d
                ON d.patient_id = s.patient_id
            LEFT JOIN medications m
                ON s.medi_id = m.medi_id
            WHERE s.sche_id = $1
              AND d.device_uid = $2
            LIMIT 1
        `;

        const schedule_result = await client.query(schedule_query, [
            numeric_fields.sche_id,
            String(device_uid).trim()
        ]);

        if (schedule_result.rows.length === 0) {
            return sendError(
                res,
                404,
                'Schedule or device not found, or device is not assigned to the schedule patient.'
            );
        }

        const schedule_row = schedule_result.rows[0];
        const sche_time = build_schedule_timestamp(schedule_row.time_to_take, parsed_event_time);
        const activity_payload = {
            patient_id: schedule_row.patient_id,
            sche_id: schedule_row.sche_id,
            sche_time: sche_time.toISOString(),
            actual_time: parsed_event_time.toISOString(),
            status: normalized_status,
            is_face_auth: parsed_face_verified ?? false,
            is_ai_check: parsed_action_verified ?? false,
            similarity_score: parsed_similarity_score
        };

        const duplicated_activity = await find_duplicate_device_activity(client, activity_payload);

        if (duplicated_activity) {
            await touch_device_last_ping_by_device_uid(client, device_uid);
            return sendSuccess(res, 200, {
                message: 'Duplicate device event ignored. Existing activity returned.',
                activity: to_activity_response(duplicated_activity),
                notification: null,
                decision: {
                    status: normalized_status,
                    face_verified: parsed_face_verified,
                    dispensed: parsed_dispensed,
                    action_verified: parsed_action_verified,
                    error_code: error_code || null
                }
            });
        }

        await client.query('BEGIN');
        transaction_started = true;

        const inserted_activity = await insert_activity(client, activity_payload);
        await touch_device_last_ping_by_device_uid(client, device_uid);

        await client.query('COMMIT');
        transaction_started = false;

        const notification_result = await trigger_activity_notification_safe({
            mem_id: schedule_row.mem_id,
            patient_id: schedule_row.patient_id,
            activity_id: inserted_activity.activity_id,
            event_type: normalized_status,
            medi_name: schedule_row.medi_name || 'Registered medication',
            error_code
        });

        if (normalized_status === ACTIVITY_STATUS.SUCCESS) {
            const low_stock_snapshot = await get_low_stock_snapshot_for_schedule_safe(schedule_row.sche_id);

            if (low_stock_snapshot.calculable && low_stock_snapshot.should_trigger) {
                await trigger_low_stock_notification({
                    mem_id: schedule_row.mem_id,
                    patient_id: schedule_row.patient_id,
                    activity_id: inserted_activity.activity_id,
                    medi_name: low_stock_snapshot.base_schedule?.medi_name || schedule_row.medi_name,
                    remaining_quantity: low_stock_snapshot.remaining_quantity
                });
            }
        }

        return sendSuccess(res, 201, {
            message: 'Device medication event saved successfully.',
            activity: to_activity_response(inserted_activity),
            notification: notification_result.notification,
            decision: {
                status: normalized_status,
                face_verified: parsed_face_verified,
                dispensed: parsed_dispensed,
                action_verified: parsed_action_verified,
                error_code: error_code || null
            }
        });
    } catch (error) {
        if (transaction_started) {
            await client.query('ROLLBACK');
        }
        console.error('Device activity create error:', error);
        return sendError(res, 500, 'Server error while saving device medication event.');
    } finally {
        client.release();
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
                activity_id,
                patient_id,
                sche_id,
                sche_time,
                actual_time,
                status,
                is_face_auth,
                is_ai_check,
                similarity_score,
                created_at
            FROM activities
            WHERE patient_id = $1
            ORDER BY sche_time DESC NULLS LAST, activity_id DESC
        `;

        const { rows } = await pool.query(query, [patient_id]);

        return sendSuccess(res, 200, {
            activities: rows.map(to_activity_response)
        });
    } catch (error) {
        console.error('Activity fetch error:', error);
        return sendError(res, 500, 'Server error while fetching activities.');
    }
});

module.exports = router;
