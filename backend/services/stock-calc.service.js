const pool = require('../db');
const { COMPLETED_STATUSES } = require('../utils/dashboard-helpers');

const LOW_STOCK_THRESHOLD = 3;
const DAY_IN_MS = 24 * 60 * 60 * 1000;

const normalize_date_only = (value) => {
    if (!value) {
        return null;
    }

    const date = new Date(value);

    if (Number.isNaN(date.getTime())) {
        return null;
    }

    return new Date(Date.UTC(
        date.getUTCFullYear(),
        date.getUTCMonth(),
        date.getUTCDate()
    ));
};

const get_schedule_step_days = (schedule) => {
    const parsed_interval = Number(schedule.dose_interval);

    if (Number.isInteger(parsed_interval) && parsed_interval > 0) {
        return parsed_interval;
    }

    return 1;
};

const build_schedule_datetime = (date, time_value) => {
    if (!time_value) {
        return null;
    }

    const [hours = 0, minutes = 0, seconds = 0] = String(time_value)
        .split(':')
        .map(Number);
    const schedule_datetime = new Date(date);
    schedule_datetime.setUTCHours(hours, minutes, seconds || 0, 0);

    return schedule_datetime;
};

const should_include_planned_schedule_date = (schedule, schedule_date) => {
    if (!schedule.created_at) {
        return true;
    }

    const created_at = new Date(schedule.created_at);

    if (Number.isNaN(created_at.getTime())) {
        return true;
    }

    const created_date = normalize_date_only(created_at);

    if (!created_date) {
        return true;
    }

    if (schedule_date.getTime() > created_date.getTime()) {
        return true;
    }

    if (schedule_date.getTime() < created_date.getTime()) {
        return false;
    }

    const schedule_datetime = build_schedule_datetime(
        schedule_date,
        schedule.time_to_take
    );

    if (!schedule_datetime) {
        return true;
    }

    return schedule_datetime.getTime() >= created_at.getTime();
};

const get_planned_quantity_for_one_schedule = (schedule) => {
    const start_date = normalize_date_only(schedule.start_date);
    const end_date = normalize_date_only(schedule.end_date);

    if (!start_date || !end_date) {
        return {
            calculable: false,
            planned_quantity: null,
            reason: 'end_date is required to calculate LOW_STOCK in the current schema.'
        };
    }

    if (end_date.getTime() < start_date.getTime()) {
        return {
            calculable: false,
            planned_quantity: null,
            reason: 'end_date is earlier than start_date.'
        };
    }

    const step_days = get_schedule_step_days(schedule);
    let planned_quantity = 0;

    for (
        let current_date = new Date(start_date);
        current_date.getTime() <= end_date.getTime();
        current_date = new Date(current_date.getTime() + (step_days * DAY_IN_MS))
    ) {
        if (should_include_planned_schedule_date(schedule, current_date)) {
            planned_quantity += 1;
        }
    }

    return {
        calculable: true,
        planned_quantity
    };
};

const should_trigger_low_stock = (remaining_quantity) => {
    if (remaining_quantity === null || remaining_quantity === undefined) {
        return false;
    }

    return remaining_quantity <= LOW_STOCK_THRESHOLD;
};

const find_base_schedule = async (executor, sche_id) => {
    const query = `
        SELECT
            s.sche_id,
            s.patient_id,
            s.medi_id,
            s.start_date,
            s.end_date,
            s.time_to_take,
            s.dose_interval,
            s.status,
            s.created_at,
            m.medi_name
        FROM schedules s
        LEFT JOIN medications m
            ON s.medi_id = m.medi_id
        WHERE s.sche_id = $1
        LIMIT 1
    `;

    const { rows } = await executor.query(query, [sche_id]);
    return rows[0] || null;
};

const find_group_schedules = async (executor, base_schedule) => {
    const query = `
        SELECT
            s.sche_id,
            s.patient_id,
            s.medi_id,
            s.start_date,
            s.end_date,
            s.time_to_take,
            s.dose_interval,
            s.status,
            s.created_at,
            m.medi_name
        FROM schedules s
        LEFT JOIN medications m
            ON s.medi_id = m.medi_id
        WHERE s.patient_id = $1
          AND s.start_date = $2
          AND s.end_date = $3
          AND s.dose_interval = $4
          AND s.status = $5
        ORDER BY s.time_to_take ASC, s.sche_id ASC
    `;

    const { rows } = await executor.query(query, [
        base_schedule.patient_id,
        base_schedule.start_date,
        base_schedule.end_date,
        base_schedule.dose_interval,
        base_schedule.status
    ]);

    return rows;
};

const get_total_planned_quantity_for_group = (group_schedules) => {
    let total_planned_quantity = 0;

    for (const schedule of group_schedules) {
        const planned_result = get_planned_quantity_for_one_schedule(schedule);

        if (!planned_result.calculable) {
            return {
                calculable: false,
                total_planned_quantity: null,
                reason: planned_result.reason
            };
        }

        total_planned_quantity += planned_result.planned_quantity;
    }

    return {
        calculable: true,
        total_planned_quantity
    };
};

const get_consumed_quantity_for_group = async (executor, group_sche_ids) => {
    if (!Array.isArray(group_sche_ids) || group_sche_ids.length === 0) {
        return 0;
    }

    const query = `
        SELECT COUNT(*)::int AS consumed_quantity
        FROM activities
        WHERE sche_id = ANY($1::int[])
          AND UPPER(status) = ANY($2::text[])
    `;

    const { rows } = await executor.query(query, [group_sche_ids, COMPLETED_STATUSES]);
    return rows[0]?.consumed_quantity || 0;
};

const get_low_stock_snapshot_for_schedule = async (executor, sche_id) => {
    const base_schedule = await find_base_schedule(executor, sche_id);

    if (!base_schedule) {
        return {
            calculable: false,
            reason: 'Schedule not found.',
            base_schedule: null,
            group_schedules: [],
            group_sche_ids: [],
            total_planned_quantity: null,
            consumed_quantity: null,
            remaining_quantity: null,
            should_trigger: false
        };
    }

    const group_schedules = await find_group_schedules(executor, base_schedule);

    if (group_schedules.length === 0) {
        return {
            calculable: false,
            reason: 'Schedule group not found.',
            base_schedule,
            group_schedules: [],
            group_sche_ids: [],
            total_planned_quantity: null,
            consumed_quantity: null,
            remaining_quantity: null,
            should_trigger: false
        };
    }

    const total_planned_result = get_total_planned_quantity_for_group(group_schedules);
    const group_sche_ids = group_schedules.map((schedule) => schedule.sche_id);

    if (!total_planned_result.calculable) {
        return {
            calculable: false,
            reason: total_planned_result.reason,
            base_schedule,
            group_schedules,
            group_sche_ids,
            total_planned_quantity: null,
            consumed_quantity: null,
            remaining_quantity: null,
            should_trigger: false
        };
    }

    const consumed_quantity = await get_consumed_quantity_for_group(executor, group_sche_ids);
    const remaining_quantity = Math.max(
        total_planned_result.total_planned_quantity - consumed_quantity,
        0
    );

    return {
        calculable: true,
        reason: null,
        base_schedule,
        group_schedules,
        group_sche_ids,
        total_planned_quantity: total_planned_result.total_planned_quantity,
        consumed_quantity,
        remaining_quantity,
        should_trigger: should_trigger_low_stock(remaining_quantity)
    };
};

const get_low_stock_snapshot_for_schedule_safe = async (sche_id) => {
    try {
        return await get_low_stock_snapshot_for_schedule(pool, sche_id);
    } catch (error) {
        console.error('[LOW-STOCK] failed to calculate remaining quantity:', error);
        return {
            calculable: false,
            reason: 'Failed to calculate low stock snapshot.',
            base_schedule: null,
            group_schedules: [],
            group_sche_ids: [],
            total_planned_quantity: null,
            consumed_quantity: null,
            remaining_quantity: null,
            should_trigger: false,
            error
        };
    }
};

module.exports = {
    LOW_STOCK_THRESHOLD,
    get_planned_quantity_for_one_schedule,
    should_trigger_low_stock,
    find_base_schedule,
    find_group_schedules,
    get_total_planned_quantity_for_group,
    get_consumed_quantity_for_group,
    get_low_stock_snapshot_for_schedule,
    get_low_stock_snapshot_for_schedule_safe
};
