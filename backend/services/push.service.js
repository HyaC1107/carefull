const pool = require('../db');
const { COMPLETED_STATUSES, MISSED_STATUSES } = require('../utils/dashboard-helpers');
const { get_messaging } = require('./firebase-admin.service');

const PUSH_EVENT_TYPE = {
    COMPLETED: 'COMPLETED',
    MISSED: 'MISSED'
};

const resolve_push_event_type = (status) => {
    const normalized_status = String(status || '').toUpperCase();

    if (COMPLETED_STATUSES.includes(normalized_status)) {
        return PUSH_EVENT_TYPE.COMPLETED;
    }

    if (MISSED_STATUSES.includes(normalized_status)) {
        return PUSH_EVENT_TYPE.MISSED;
    }

    return null;
};

const format_push_time = (value) => {
    if (!value) {
        return '-';
    }

    const date = new Date(value);

    if (Number.isNaN(date.getTime())) {
        return String(value);
    }

    return date.toLocaleTimeString('ko-KR', {
        hour: '2-digit',
        minute: '2-digit'
    });
};

const build_activity_push_message = (row) => {
    const event_type = resolve_push_event_type(row.status);
    const patient_name = row.patient_name || '환자';

    if (event_type === PUSH_EVENT_TYPE.COMPLETED) {
        return {
            title: '복약 완료',
            body: `${patient_name}님이 ${format_push_time(row.actual_time || row.sche_time)}에 복약을 완료했습니다.`
        };
    }

    if (event_type === PUSH_EVENT_TYPE.MISSED) {
        return {
            title: '미복용 알림',
            body: `${patient_name}님이 ${format_push_time(row.sche_time)} 복약을 완료하지 않았습니다.`
        };
    }

    return null;
};

const get_active_push_tokens_by_mem_id = async (mem_id) => {
    const query = `
        SELECT fcm_token
        FROM push_tokens
        WHERE mem_id = $1
          AND is_active = TRUE
    `;

    const { rows } = await pool.query(query, [mem_id]);
    return rows.map((row) => row.fcm_token).filter(Boolean);
};

const get_token_prefixes = (tokens) => (
    tokens.map((token) => String(token || '').slice(0, 12)).filter(Boolean)
);

const INVALID_FCM_TOKEN_CODES = new Set([
    'messaging/registration-token-not-registered',
    'messaging/invalid-registration-token'
]);

const summarize_firebase_failures = (responses = []) => {
    const failures = {};

    responses.forEach((response) => {
        if (response.success) return;

        const code = response.error?.code || 'unknown';
        failures[code] = (failures[code] || 0) + 1;
    });

    return failures;
};

const deactivate_invalid_push_tokens = async (tokens, responses = []) => {
    const invalid_tokens = responses
        .map((response, index) => (
            INVALID_FCM_TOKEN_CODES.has(response.error?.code) ? tokens[index] : null
        ))
        .filter(Boolean);

    if (invalid_tokens.length === 0) {
        return 0;
    }

    const { rowCount } = await pool.query(
        `
            UPDATE push_tokens
            SET
                is_active = FALSE,
                updated_at = CURRENT_TIMESTAMP
            WHERE fcm_token = ANY($1::text[])
        `,
        [invalid_tokens]
    );

    return rowCount;
};

const send_to_tokens = async ({ mem_id, tokens, title, body, data = {}, context = 'unknown' }) => {
    const token_count = tokens.length;
    const token_prefixes = get_token_prefixes(tokens);

    console.info('[PUSH] send request:', {
        mem_id,
        context,
        token_count,
        token_prefixes
    });

    if (!tokens.length) {
        console.warn('[PUSH] skipped: active push token not found', { mem_id, context });

        return {
            success_count: 0,
            failure_count: 0,
            deactivated_count: 0,
            failures: {}
        };
    }

    const response = await get_messaging().sendEachForMulticast({
        tokens,
        notification: {
            title,
            body
        },
        data
    });

    const failures = summarize_firebase_failures(response.responses);
    const deactivated_count = await deactivate_invalid_push_tokens(tokens, response.responses);

    console.info('[PUSH] send result:', {
        mem_id,
        context,
        success_count: response.successCount,
        failure_count: response.failureCount,
        deactivated_count,
        failures
    });

    return {
        success_count: response.successCount,
        failure_count: response.failureCount,
        deactivated_count,
        failures
    };
};

const register_push_token = async ({ mem_id, fcm_token, device_type = 'web' }) => {
    const client = await pool.connect();
    const query = `
        INSERT INTO push_tokens (
            mem_id,
            fcm_token,
            device_type,
            is_active,
            created_at,
            updated_at
        )
        VALUES ($1, $2, $3, TRUE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        ON CONFLICT (fcm_token)
        DO UPDATE SET
            mem_id = EXCLUDED.mem_id,
            device_type = EXCLUDED.device_type,
            is_active = TRUE,
            updated_at = CURRENT_TIMESTAMP
        RETURNING
            push_token_id,
            mem_id,
            fcm_token,
            device_type,
            is_active,
            created_at,
            updated_at
    `;

    try {
        await client.query('BEGIN');
        const { rows } = await client.query(query, [mem_id, fcm_token, device_type]);
        await client.query('COMMIT');
        return rows[0] || null;
    } catch (error) {
        await client.query('ROLLBACK');
        throw error;
    } finally {
        client.release();
    }
};

const send_test_push = async (mem_id) => {
    const tokens = await get_active_push_tokens_by_mem_id(mem_id);

    return send_to_tokens({
        mem_id,
        tokens,
        context: 'test',
        title: '푸시 테스트',
        body: 'Carefull 푸시 알림 테스트입니다.',
        data: {
            type: 'TEST'
        }
    });
};

const send_schedule_created_push = async (mem_id) => {
    const tokens = await get_active_push_tokens_by_mem_id(mem_id);

    if (tokens.length === 0) {
        console.warn('[PUSH] skipped: active push token not found', {
            mem_id,
            context: 'schedule_created'
        });

        return {
            sent: false,
            reason: 'active push token not found'
        };
    }

    const result = await send_to_tokens({
        mem_id,
        tokens,
        context: 'schedule_created',
        title: '복약 스케줄 등록 완료',
        body: '새 복약 스케줄이 등록되었습니다.',
        data: {
            type: 'SCHEDULE_CREATED'
        }
    });

    return {
        sent: result.success_count > 0,
        ...result
    };
};

const send_medication_activity_push = async (activity_id) => {
    const query = `
        SELECT
            a.activity_id,
            a.sche_id,
            a.sche_time,
            a.actual_time,
            a.status,
            s.patient_id,
            p.mem_id,
            p.patient_name,
            pt.fcm_token
        FROM activities a
        INNER JOIN schedules s
            ON s.sche_id = a.sche_id
        INNER JOIN patients p
            ON p.patient_id = s.patient_id
        LEFT JOIN push_tokens pt
            ON pt.mem_id = p.mem_id
           AND pt.is_active = TRUE
        WHERE a.activity_id = $1
    `;

    const { rows } = await pool.query(query, [activity_id]);
    const activity = rows[0] || null;

    if (!activity) {
        console.warn('[PUSH] skipped: activity not found', { activity_id });

        return {
            sent: false,
            reason: 'activity not found'
        };
    }

    const message = build_activity_push_message(activity);

    if (!message) {
        console.warn('[PUSH] skipped: unsupported activity status', {
            activity_id,
            status: activity.status
        });

        return {
            sent: false,
            reason: 'unsupported activity status'
        };
    }

    const tokens = rows.map((row) => row.fcm_token).filter(Boolean);

    if (tokens.length === 0) {
        console.warn('[PUSH] skipped: active push token not found', {
            mem_id: activity.mem_id,
            context: 'medication_activity',
            activity_id
        });

        return {
            sent: false,
            reason: 'active push token not found'
        };
    }

    const result = await send_to_tokens({
        mem_id: activity.mem_id,
        tokens,
        context: 'medication_activity',
        ...message,
        data: {
            type: resolve_push_event_type(activity.status),
            activity_id: String(activity.activity_id),
            sche_id: String(activity.sche_id),
            patient_id: String(activity.patient_id)
        }
    });

    return {
        sent: result.success_count > 0,
        ...result
    };
};

const send_medication_activity_push_safe = async (activity_id) => {
    try {
        return await send_medication_activity_push(activity_id);
    } catch (error) {
        console.error('[PUSH] failed to send medication activity push:', error);
        return {
            sent: false,
            error
        };
    }
};

const send_schedule_created_push_safe = async (mem_id) => {
    try {
        return await send_schedule_created_push(mem_id);
    } catch (error) {
        console.warn('[PUSH] failed to send schedule created push:', error);
        return {
            sent: false,
            error
        };
    }
};

module.exports = {
    register_push_token,
    send_test_push,
    send_schedule_created_push_safe,
    send_medication_activity_push_safe
};
