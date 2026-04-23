const pool = require('../db');
const { ACTIVITY_STATUS } = require('../utils/activity-status');

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

const create_notification = async (executor, {
    mem_id,
    patient_id,
    activity_id,
    event_type,
    medi_name,
    error_code,
    remaining_quantity
}) => {
    const notification_content = build_notification_content({
        event_type,
        medi_name,
        error_code,
        remaining_quantity
    });

    const existing_notification = await find_existing_notification(
        executor,
        activity_id,
        notification_content.noti_type
    );

    if (existing_notification) {
        return {
            notification: to_notification_response(existing_notification),
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
        return await create_notification(pool, payload);
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
