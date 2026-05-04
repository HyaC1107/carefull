const pool = require('../db');
const { ACTIVITY_STATUS } = require('../utils/activity-status');
const { COMPLETED_STATUSES, MISSED_STATUSES } = require('../utils/dashboard-helpers');
const { send_medication_activity_push_safe } = require('./push.service');

const NOTIFICATION_TYPE = {
    SUCCESS: ACTIVITY_STATUS.SUCCESS,
    FAILED: ACTIVITY_STATUS.FAILED,
    MISSED: ACTIVITY_STATUS.MISSED,
    ERROR: ACTIVITY_STATUS.ERROR,
    LOW_STOCK: 'LOW_STOCK'
};

const build_notification_content = ({
    event_type,
    medi_name,
    error_code,
    remaining_quantity
}) => {
    const resolved_medi_name = medi_name || '등록된 복약 스케줄';

    if (event_type === NOTIFICATION_TYPE.SUCCESS) {
        return {
            noti_title: '복약 완료',
            noti_msg: `${resolved_medi_name} 복약이 정상적으로 완료되었습니다.`,
            noti_type: NOTIFICATION_TYPE.SUCCESS
        };
    }

    if (event_type === NOTIFICATION_TYPE.ERROR) {
        return {
            noti_title: '복약 기기 오류',
            noti_msg: error_code
                ? `${resolved_medi_name} 처리 중 기기 오류가 발생했습니다. (${error_code})`
                : `${resolved_medi_name} 처리 중 기기 오류가 발생했습니다.`,
            noti_type: NOTIFICATION_TYPE.ERROR
        };
    }

    if (event_type === NOTIFICATION_TYPE.MISSED) {
        return {
            noti_title: '미복약 알림',
            noti_msg: `${resolved_medi_name} 복약 예정 시간이 지났지만 복약 기록이 없습니다.`,
            noti_type: NOTIFICATION_TYPE.MISSED
        };
    }

    if (event_type === NOTIFICATION_TYPE.LOW_STOCK) {
        return {
            noti_title: '약 부족 알림',
            noti_msg: remaining_quantity === null || remaining_quantity === undefined
                ? `${resolved_medi_name} 기준 남은 복약 가능 횟수가 부족합니다.`
                : `${resolved_medi_name} 기준 남은 복약 가능 횟수가 ${remaining_quantity}회분입니다.`,
            noti_type: NOTIFICATION_TYPE.LOW_STOCK
        };
    }

    return {
        noti_title: '복약 실패',
        noti_msg: `${resolved_medi_name} 복약 시도가 있었지만 정상 완료되지 않았습니다.`,
        noti_type: NOTIFICATION_TYPE.FAILED
    };
};

const to_notification_response = (row) => row
    ? {
        noti_id: row.noti_id,
        mem_id: row.mem_id,
        activity_id: row.activity_id,
        noti_title: row.noti_title,
        noti_msg: row.noti_msg,
        is_received: row.is_received,
        noti_type: row.noti_type,
        created_at: row.created_at
    }
    : null;

const find_existing_notification = async (executor, activity_id, noti_type) => {
    const query = `
        SELECT
            noti_id,
            mem_id,
            activity_id,
            noti_title,
            noti_msg,
            is_received,
            noti_type,
            created_at
        FROM notifications
        WHERE activity_id = $1
          AND noti_type = $2
        LIMIT 1
    `;

    const { rows } = await executor.query(query, [activity_id, noti_type]);
    return rows[0] || null;
};

const find_existing_missed_notification_for_schedule_date = async (
    executor,
    patient_id,
    activity_id,
    noti_type
) => {
    if (noti_type !== NOTIFICATION_TYPE.MISSED) {
        return null;
    }

    const query = `
        SELECT
            n.noti_id,
            n.mem_id,
            n.activity_id,
            n.noti_title,
            n.noti_msg,
            n.is_received,
            n.noti_type,
            n.created_at
        FROM notifications n
        INNER JOIN activities existing_activity
            ON n.activity_id = existing_activity.activity_id
        INNER JOIN activities current_activity
            ON current_activity.activity_id = $2
        WHERE n.patient_id = $1
          AND n.noti_type = $3
          AND existing_activity.patient_id = current_activity.patient_id
          AND existing_activity.sche_id = current_activity.sche_id
          AND (existing_activity.sche_time AT TIME ZONE 'Asia/Seoul')::date =
              (current_activity.sche_time AT TIME ZONE 'Asia/Seoul')::date
        LIMIT 1
    `;

    const { rows } = await executor.query(query, [
        patient_id,
        activity_id,
        noti_type
    ]);
    return rows[0] || null;
};

const find_existing_low_stock_notification_for_medication_date = async (
    executor,
    patient_id,
    activity_id,
    noti_type
) => {
    if (noti_type !== NOTIFICATION_TYPE.LOW_STOCK) {
        return null;
    }

    const query = `
        SELECT
            n.noti_id,
            n.mem_id,
            n.activity_id,
            n.noti_title,
            n.noti_msg,
            n.is_received,
            n.noti_type,
            n.created_at
        FROM notifications n
        INNER JOIN activities existing_activity
            ON n.activity_id = existing_activity.activity_id
        INNER JOIN schedules existing_schedule
            ON existing_activity.sche_id = existing_schedule.sche_id
        INNER JOIN activities current_activity
            ON current_activity.activity_id = $2
        INNER JOIN schedules current_schedule
            ON current_activity.sche_id = current_schedule.sche_id
        WHERE n.patient_id = $1
          AND n.noti_type = $3
          AND existing_activity.patient_id = current_activity.patient_id
          AND existing_schedule.medi_id = current_schedule.medi_id
          AND (n.created_at AT TIME ZONE 'Asia/Seoul')::date =
              (CURRENT_TIMESTAMP AT TIME ZONE 'Asia/Seoul')::date
        LIMIT 1
    `;

    const { rows } = await executor.query(query, [
        patient_id,
        activity_id,
        noti_type
    ]);
    return rows[0] || null;
};

const create_notification = async (executor, {
    mem_id,
    patient_id,
    activity_id,
    event_type,
    medi_name,
    error_code,
    remaining_quantity
}) => {
    console.info('[NOTIFICATION-TRIGGER] create requested:', {
        mem_id,
        patient_id,
        activity_id,
        event_type
    });

    const notification_content = build_notification_content({
        event_type,
        medi_name,
        error_code,
        remaining_quantity
    });

    console.info('[NOTIFICATION-TRIGGER] content resolved:', {
        activity_id,
        noti_type: notification_content.noti_type
    });

    const existing_notification = await find_existing_notification(
        executor,
        activity_id,
        notification_content.noti_type
    );

    if (existing_notification) {
        console.info('[NOTIFICATION-TRIGGER] existing notification found:', {
            activity_id,
            noti_type: notification_content.noti_type
        });

        return {
            notification: to_notification_response(existing_notification),
            created: false
        };
    }

    const existing_missed_notification = await find_existing_missed_notification_for_schedule_date(
        executor,
        patient_id,
        activity_id,
        notification_content.noti_type
    );

    if (existing_missed_notification) {
        console.info('[NOTIFICATION-TRIGGER] existing missed notification found:', {
            activity_id,
            noti_type: notification_content.noti_type
        });

        return {
            notification: to_notification_response(existing_missed_notification),
            created: false
        };
    }

    const existing_low_stock_notification = await find_existing_low_stock_notification_for_medication_date(
        executor,
        patient_id,
        activity_id,
        notification_content.noti_type
    );

    if (existing_low_stock_notification) {
        console.info('[NOTIFICATION-TRIGGER] existing low stock notification found:', {
            activity_id,
            noti_type: notification_content.noti_type
        });

        return {
            notification: to_notification_response(existing_low_stock_notification),
            created: false
        };
    }

    const insert_query = `
        INSERT INTO notifications (
            mem_id,
            patient_id,
            activity_id,
            noti_title,
            noti_msg,
            is_received,
            received_time,
            noti_type
        )
        VALUES ($1, $2, $3, $4, $5, FALSE, CURRENT_TIMESTAMP, $6)
        RETURNING
            noti_id,
            mem_id,
            activity_id,
            noti_title,
            noti_msg,
            is_received,
            noti_type,
            created_at
    `;

    const { rows } = await executor.query(insert_query, [
        mem_id,
        patient_id,
        activity_id,
        notification_content.noti_title,
        notification_content.noti_msg,
        notification_content.noti_type
    ]);

    console.info('[NOTIFICATION-TRIGGER] notification created:', {
        activity_id,
        noti_id: rows[0]?.noti_id,
        noti_type: notification_content.noti_type
    });

    if (
        [...COMPLETED_STATUSES, ...MISSED_STATUSES].includes(notification_content.noti_type)
    ) {
        console.info('[NOTIFICATION-TRIGGER] push firing:', {
            activity_id,
            noti_type: notification_content.noti_type
        });

        const push_result = await send_medication_activity_push_safe(activity_id);

        console.info('[NOTIFICATION-TRIGGER] push result:', {
            activity_id,
            noti_type: notification_content.noti_type,
            sent: push_result?.sent,
            success_count: push_result?.success_count,
            failure_count: push_result?.failure_count,
            reason: push_result?.reason
        });
    }

    return {
        notification: to_notification_response(rows[0]),
        created: true
    };
};

const trigger_activity_notification = async (executor, payload) => {
    return create_notification(executor, payload);
};

const trigger_activity_notification_safe = async (payload) => {
    try {
        const result = await create_notification(pool, payload);

        return result;
    } catch (error) {
        console.error('[NOTIFICATION-TRIGGER] failed to create notification:', error);
        return {
            notification: null,
            created: false,
            error
        };
    }
};

const trigger_low_stock_notification = async (payload) => {
    if (!payload?.activity_id) {
        return {
            notification: null,
            created: false,
            reason: 'activity_id is required for LOW_STOCK notification in the current schema.'
        };
    }

    return trigger_activity_notification_safe({
        ...payload,
        event_type: NOTIFICATION_TYPE.LOW_STOCK
    });
};

module.exports = {
    NOTIFICATION_TYPE,
    build_notification_content,
    trigger_activity_notification,
    trigger_activity_notification_safe,
    trigger_low_stock_notification,
    to_notification_response
};
