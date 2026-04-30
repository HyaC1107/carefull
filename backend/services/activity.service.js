const pool = require('../db');
const { find_patient_id_by_mem_id } = require('../utils/auth-user');
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
} = require('./notification-trigger.service');
const {
    get_low_stock_snapshot_for_schedule_safe
} = require('./stock-calc.service');
const {
    buildKstDateTimeString
} = require('../utils/dashboard-helpers');

const ALLOWED_ACTIVITY_STATUSES = [
    ACTIVITY_STATUS.SUCCESS,
    ACTIVITY_STATUS.FAILED,
    ACTIVITY_STATUS.MISSED,
    ACTIVITY_STATUS.ERROR
];

const create_service_error = (status_code, message, extra = {}) => {
    const error = new Error(message);
    error.status_code = status_code;
    error.extra = extra;
    return error;
};

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
    device_uid: body.device_uid ?? null,
    sche_id: body.sche_id ?? null,
    event_time: body.event_time ?? null,
    status: body.status ?? null,
    face_verified: body.face_verified ?? null,
    dispensed: body.dispensed ?? null,
    action_verified: body.action_verified ?? null,
    error_code: body.error_code ?? null,
    raw_confidence: body.raw_confidence ?? null
});

const build_schedule_timestamp = (time_to_take, base_date) => {
    return buildKstDateTimeString(base_date, time_to_take);
};

const insert_activity = async (executor, payload) => {
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

    const { rows } = await executor.query(insert_query, [
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

const find_duplicate_device_activity = async (executor, payload) => {
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

    const { rows } = await executor.query(duplicate_query, [
        payload.patient_id,
        payload.sche_id,
        payload.sche_time,
        payload.actual_time
    ]);

    return rows[0] || null;
};

const find_schedule_for_patient = async (executor, sche_id, patient_id) => {
    const query = `
        SELECT
            sche_id,
            patient_id
        FROM schedules
        WHERE sche_id = $1
          AND patient_id = $2
        LIMIT 1
    `;

    const { rows } = await executor.query(query, [sche_id, patient_id]);
    return rows[0] || null;
};

const find_medication_name_by_sche_id = async (executor, sche_id) => {
    const query = `
        SELECT m.medi_name
        FROM schedules s
        INNER JOIN medications m
            ON s.medi_id = m.medi_id
        WHERE s.sche_id = $1
        LIMIT 1
    `;

    const { rows } = await executor.query(query, [sche_id]);
    return rows[0]?.medi_name || null;
};

const find_schedule_for_device = async (executor, sche_id, device_uid) => {
    const query = `
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

    const { rows } = await executor.query(query, [sche_id, device_uid]);
    return rows[0] || null;
};

const parse_similarity_score = (value, field_name = 'similarity_score') => {
    if (value === undefined || value === null || value === '') {
        return 0;
    }

    const parsed_value = parseNumericValue(value);

    if (parsed_value === null) {
        throw create_service_error(400, `${field_name} must be numeric.`);
    }

    return parsed_value;
};

const trigger_success_side_effects = async ({
    mem_id,
    patient_id,
    activity_id,
    sche_id,
    fallback_medi_name
}) => {
    const medi_name = fallback_medi_name || await find_medication_name_by_sche_id(pool, sche_id) || 'Registered medication';

    const notification_result = await trigger_activity_notification_safe({
        mem_id,
        patient_id,
        activity_id,
        event_type: NOTIFICATION_TYPE.SUCCESS,
        medi_name
    });

    const low_stock_snapshot = await get_low_stock_snapshot_for_schedule_safe(sche_id);

    if (low_stock_snapshot.calculable && low_stock_snapshot.should_trigger) {
        await trigger_low_stock_notification({
            mem_id,
            patient_id,
            activity_id,
            medi_name: low_stock_snapshot.base_schedule?.medi_name || medi_name,
            remaining_quantity: low_stock_snapshot.remaining_quantity
        });
    }

    return notification_result.notification;
};

const create_manual_activity = async ({ mem_id, body }) => {
    const { sche_time, actual_time, status, is_face_auth, is_ai_check } = body;

    if (!sche_time) {
        throw create_service_error(400, 'sche_time is required.');
    }

    if (!status || !String(status).trim()) {
        throw create_service_error(400, 'status is required.');
    }

    const numeric_fields = parseNumericFields(body, ['sche_id']);

    if (!numeric_fields) {
        throw create_service_error(400, 'sche_id must be numeric.');
    }

    const normalized_status = String(status).trim().toUpperCase();

    if (!ALLOWED_ACTIVITY_STATUSES.includes(normalized_status)) {
        throw create_service_error(
            400,
            `status must be one of ${ALLOWED_ACTIVITY_STATUSES.join(', ')}.`
        );
    }

    const parsed_similarity_score = parse_similarity_score(body.similarity_score);
    const client = await pool.connect();
    let transaction_started = false;

    try {
        const patient_id = await find_patient_id_by_mem_id(mem_id);

        if (!patient_id) {
            throw create_service_error(404, 'Patient not found.');
        }

        const schedule = await find_schedule_for_patient(client, numeric_fields.sche_id, patient_id);

        if (!schedule) {
            throw create_service_error(404, 'Schedule not found or access denied.');
        }

        await client.query('BEGIN');
        transaction_started = true;

        const inserted_activity = await insert_activity(client, {
            patient_id,
            sche_id: numeric_fields.sche_id,
            sche_time,
            actual_time: actual_time || null,
            status: normalized_status,
            is_face_auth: is_face_auth ?? false,
            is_ai_check: is_ai_check ?? false,
            similarity_score: parsed_similarity_score
        });

        await client.query('COMMIT');
        transaction_started = false;

        const activity = to_activity_response(inserted_activity);
        let notification = null;

        if (normalized_status === ACTIVITY_STATUS.SUCCESS) {
            notification = await trigger_success_side_effects({
                mem_id,
                patient_id,
                activity_id: activity.activity_id,
                sche_id: numeric_fields.sche_id
            });
        }

        return {
            status_code: 201,
            payload: {
                message: 'Activity created successfully.',
                activity,
                notification
            }
        };
    } catch (error) {
        if (transaction_started) {
            await client.query('ROLLBACK');
        }
        throw error;
    } finally {
        client.release();
    }
};

const create_device_activity = async ({ body }) => {
    const resolved_payload = resolve_device_event_payload(body);
    const { device_uid, event_time, error_code, status } = resolved_payload;

    if (!device_uid || !String(device_uid).trim()) {
        throw create_service_error(400, 'device_uid is required.');
    }

    const numeric_fields = parseNumericFields(resolved_payload, ['sche_id']);

    if (!numeric_fields) {
        throw create_service_error(400, 'sche_id must be numeric.');
    }

    const parsed_event_time = event_time ? new Date(event_time) : new Date();

    if (Number.isNaN(parsed_event_time.getTime())) {
        throw create_service_error(400, 'event_time must be a valid datetime string.');
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

    if (!has_explicit_status && !has_raw_decision_inputs && !error_code) {
        throw create_service_error(
            400,
            'Provide either status, error_code, or all of face_verified/dispensed/action_verified.'
        );
    }

    if (!has_explicit_status && parsed_face_verified === null) {
        throw create_service_error(400, 'face_verified must be boolean.');
    }

    if (!has_explicit_status && parsed_dispensed === null) {
        throw create_service_error(400, 'dispensed must be boolean.');
    }

    if (!has_explicit_status && parsed_action_verified === null) {
        throw create_service_error(400, 'action_verified must be boolean.');
    }

    if (
        has_explicit_status &&
        !DEVICE_EVENT_ACTIVITY_STATUSES.includes(normalized_status_from_body)
    ) {
        throw create_service_error(
            400,
            `status must be one of ${DEVICE_EVENT_ACTIVITY_STATUSES.join(', ')}.`
        );
    }

    const parsed_similarity_score = parse_similarity_score(
        resolved_payload.raw_confidence,
        'raw_confidence'
    );

    const normalized_status = decideMedicationStatus({
        face_verified: parsed_face_verified,
        dispensed: parsed_dispensed,
        action_verified: parsed_action_verified,
        error_code,
        status: normalized_status_from_body
    });

    if (!DEVICE_EVENT_ACTIVITY_STATUSES.includes(normalized_status)) {
        throw create_service_error(500, 'Unable to determine final activity status.');
    }

    const client = await pool.connect();
    let transaction_started = false;

    try {
        const schedule_row = await find_schedule_for_device(
            client,
            numeric_fields.sche_id,
            String(device_uid).trim()
        );

        if (!schedule_row) {
            throw create_service_error(
                404,
                'Schedule or device not found, or device is not assigned to the schedule patient.'
            );
        }

        const sche_time = build_schedule_timestamp(schedule_row.time_to_take, parsed_event_time);
        const activity_payload = {
            patient_id: schedule_row.patient_id,
            sche_id: schedule_row.sche_id,
            sche_time,
            actual_time: parsed_event_time.toISOString(),
            status: normalized_status,
            is_face_auth: parsed_face_verified ?? false,
            is_ai_check: parsed_action_verified ?? false,
            similarity_score: parsed_similarity_score
        };

        const duplicated_activity = await find_duplicate_device_activity(client, activity_payload);

        if (duplicated_activity) {
            return {
                status_code: 200,
                payload: {
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
                }
            };
        }

        await client.query('BEGIN');
        transaction_started = true;

        const inserted_activity = await insert_activity(client, activity_payload);

        await client.query('COMMIT');
        transaction_started = false;

        let notification = await trigger_activity_notification_safe({
            mem_id: schedule_row.mem_id,
            patient_id: schedule_row.patient_id,
            activity_id: inserted_activity.activity_id,
            event_type: normalized_status,
            medi_name: schedule_row.medi_name || 'Registered medication',
            error_code
        });

        notification = notification.notification;

        if (normalized_status === ACTIVITY_STATUS.SUCCESS) {
            notification = await trigger_success_side_effects({
                mem_id: schedule_row.mem_id,
                patient_id: schedule_row.patient_id,
                activity_id: inserted_activity.activity_id,
                sche_id: schedule_row.sche_id,
                fallback_medi_name: schedule_row.medi_name || 'Registered medication'
            });
        }

        return {
            status_code: 201,
            payload: {
                message: 'Device medication event saved successfully.',
                activity: to_activity_response(inserted_activity),
                notification,
                decision: {
                    status: normalized_status,
                    face_verified: parsed_face_verified,
                    dispensed: parsed_dispensed,
                    action_verified: parsed_action_verified,
                    error_code: error_code || null
                }
            }
        };
    } catch (error) {
        if (transaction_started) {
            await client.query('ROLLBACK');
        }
        throw error;
    } finally {
        client.release();
    }
};

const get_activities_by_mem_id = async (mem_id) => {
    const patient_id = await find_patient_id_by_mem_id(mem_id);

    if (!patient_id) {
        throw create_service_error(404, 'Patient not found.');
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

    return {
        status_code: 200,
        payload: {
            activities: rows.map(to_activity_response)
        }
    };
};

module.exports = {
    create_manual_activity,
    create_device_activity,
    get_activities_by_mem_id
};
