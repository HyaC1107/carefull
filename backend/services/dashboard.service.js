const pool = require('../db');
const { find_patient_id_by_mem_id } = require('../utils/auth-user');
const {
    COMPLETED_STATUSES,
    MISSED_STATUSES,
    TEN_MINUTES_IN_MS,
    LOW_MEDICATION_THRESHOLD,
    getTodayDateString,
    getProjectDayOfWeek,
    getSummaryStatus,
    buildScheduleTimestamp,
    getScheduleStatusColor
} = require('../utils/dashboard-helpers');
const { is_device_online } = require('../utils/device-status');
const {
    trigger_low_stock_notification
} = require('./notification-trigger.service');
const {
    get_planned_quantity_for_one_schedule
} = require('./stock-calc.service');

const get_today_context = () => {
    const current_date = new Date();

    return {
        current_date,
        today_date_string: getTodayDateString(),
        today_day_of_week: getProjectDayOfWeek(current_date)
    };
};

const get_dashboard_data_by_mem_id = async (mem_id) => {
    const member = await get_member_header(mem_id);

    if (!member) {
        return null;
    }

    const patient_id = await find_patient_id_by_mem_id(mem_id);

    if (!patient_id) {
        return build_dashboard_data({
            patient: null,
            member,
            summary: null,
            device: null,
            medication_stock: {
                remainingMedicationCount: 0,
                lowStockMedications: [],
                medications: []
            },
            total_scheduled_count: 0,
            remaining_medication_count: 0,
            today_schedules: [],
            recent_notifications: await get_recent_notifications(mem_id),
            recent_activities: []
        });
    }

    const [
        patient,
        summary,
        total_scheduled_count,
        remaining_medication_count,
        device,
        medication_stock,
        today_schedules,
        recent_notifications,
        recent_activities
    ] = await Promise.all([
        get_patient_header(patient_id),
        get_dashboard_summary(patient_id),
        get_total_planned_schedule_count(patient_id),
        get_remaining_planned_medication_count(patient_id),
        get_device_status(patient_id),
        get_estimated_medication_stock(patient_id),
        get_today_schedules(patient_id),
        get_recent_notifications(mem_id),
        get_recent_activities(patient_id)
    ]);

    await trigger_low_stock_notifications_for_estimated_stock(
        mem_id,
        patient_id,
        medication_stock.lowStockMedications
    );

    const resolved_device = apply_estimated_medication_stock_to_device(
        device,
        medication_stock
    );

    const dashboard_data = build_dashboard_data({
        patient,
        member,
        summary,
        total_scheduled_count,
        remaining_medication_count,
        device: resolved_device,
        medication_stock,
        today_schedules,
        recent_notifications,
        recent_activities
    });

    return dashboard_data;
};

const build_dashboard_data = ({
    patient,
    member,
    summary,
    total_scheduled_count,
    remaining_medication_count,
    device,
    medication_stock,
    today_schedules,
    recent_notifications,
    recent_activities
}) => {
    return {
        patient_name: patient?.patient_name || null,
        guardian_name: patient?.guardian_name || null,
        patient: {
            patient_name: patient?.patient_name || null,
            birthdate: patient?.birthdate || null,
            guardian_name: patient?.guardian_name || null
        },
        member: {
            nick: member?.nick || null,
            profile_img: member?.profile_img || ''
        },
        profile_img: member?.profile_img || '',
        summary,
        total_scheduled_count,
        remaining_medication_count,
        device,
        remainingMedicationCount: medication_stock.remainingMedicationCount,
        lowStockMedications: medication_stock.lowStockMedications,
        estimatedMedicationStock: medication_stock.medications,
        today_schedules,
        recent_notifications,
        recent_activities
    };
};

const get_member_header = async (mem_id) => {
    const query = `
        SELECT nick, profile_img
        FROM members
        WHERE mem_id = $1
        LIMIT 1
    `;

    const { rows } = await pool.query(query, [mem_id]);

    return rows[0] || null;
};

const get_estimated_medication_stock = async (patient_id) => {
    const query = `
        WITH schedule_counts AS (
            SELECT
                s.medi_id,
                COALESCE(m.medi_name, '') AS medi_name,
                COUNT(*)::int AS total_schedule_count
            FROM schedules s
            LEFT JOIN medications m
                ON m.medi_id = s.medi_id
            WHERE s.patient_id = $1
              AND UPPER(COALESCE(s.status, '')) NOT IN ('INACTIVE', 'DELETED')
            GROUP BY s.medi_id, m.medi_name
        ),
        completed_counts AS (
            SELECT
                s.medi_id,
                COUNT(a.activity_id)::int AS completed_count
            FROM activities a
            INNER JOIN schedules s
                ON s.sche_id = a.sche_id
            WHERE a.patient_id = $1
              AND UPPER(a.status) = ANY($2::text[])
            GROUP BY s.medi_id
        ),
        latest_activity AS (
            SELECT DISTINCT ON (s.medi_id)
                s.medi_id,
                a.activity_id
            FROM activities a
            INNER JOIN schedules s
                ON s.sche_id = a.sche_id
            WHERE a.patient_id = $1
            ORDER BY s.medi_id, a.created_at DESC, a.activity_id DESC
        )
        SELECT
            sc.medi_id,
            sc.medi_name,
            sc.total_schedule_count,
            COALESCE(cc.completed_count, 0)::int AS completed_count,
            GREATEST(
                sc.total_schedule_count - COALESCE(cc.completed_count, 0),
                0
            )::int AS remaining_count,
            la.activity_id
        FROM schedule_counts sc
        LEFT JOIN completed_counts cc
            ON cc.medi_id = sc.medi_id
        LEFT JOIN latest_activity la
            ON la.medi_id = sc.medi_id
        ORDER BY remaining_count ASC, sc.medi_id ASC
    `;

    const { rows } = await pool.query(query, [patient_id, COMPLETED_STATUSES]);
    const medications = rows.map((row) => ({
        medi_id: row.medi_id,
        medi_name: row.medi_name || null,
        total_schedule_count: row.total_schedule_count,
        completed_count: row.completed_count,
        remaining_count: row.remaining_count,
        activity_id: row.activity_id || null,
        is_low_stock: row.remaining_count <= LOW_MEDICATION_THRESHOLD
    }));

    const remainingMedicationCount = medications.reduce(
        (sum, item) => sum + item.remaining_count,
        0
    );

    const minimumRemainingMedicationCount = medications.length > 0
        ? Math.min(...medications.map((item) => item.remaining_count))
        : null;

    const lowStockMedications = medications.filter(
        (item) => item.is_low_stock
    );

    return {
        remainingMedicationCount,
        minimumRemainingMedicationCount,
        lowStockMedications,
        medications
    };
};

const apply_estimated_medication_stock_to_device = (device, medication_stock) => {
    if (!device) {
        return device;
    }

    const has_low_stock = medication_stock.lowStockMedications.length > 0;
    const remainingMedicationCount =
        medication_stock.remainingMedicationCount || 0;
    const minimumRemainingMedicationCount =
        medication_stock.minimumRemainingMedicationCount ?? 0;

    return {
        ...device,
        medication_level: medication_stock.remainingMedicationCount ?? 0,
        remainingCount: remainingMedicationCount,
        remainingMedicationCount: remainingMedicationCount,
        lowStockMedications: medication_stock.lowStockMedications,
        status_color: has_low_stock ? 'orange' : device.status_color,
        status_message: has_low_stock ? 'Warning' : device.status_message,
        status_reason: has_low_stock
            ? 'Schedule-based estimated remaining medication count is low.'
            : device.status_reason
    };
};

const trigger_low_stock_notifications_for_estimated_stock = async (
    mem_id,
    patient_id,
    low_stock_medications
) => {
    for (const medication of low_stock_medications) {
        if (!medication.activity_id) {
            console.log(
                `[LOW-STOCK] skipped notification because no activity_id is available for medi_id: ${medication.medi_id}`
            );
            continue;
        }

        await trigger_low_stock_notification({
            mem_id,
            patient_id,
            activity_id: medication.activity_id,
            medi_name: medication.medi_name,
            remaining_quantity: medication.remaining_count
        });
    }
};

const get_patient_header = async (patient_id) => {
    const query = `
        SELECT
            patient_name,
            birthdate,
            guardian_name
        FROM patients
        WHERE patient_id = $1
        LIMIT 1
    `;

    const { rows } = await pool.query(query, [patient_id]);

    return rows[0] || null;
};

const get_dashboard_summary = async (patient_id) => {
    const { today_date_string } = get_today_context();

    const total_scheduled_query = `
        SELECT COUNT(*)::int AS count
        FROM schedules
        WHERE patient_id = $1
          AND status = 'ACTIVE'
          AND start_date <= $2::date
          AND (end_date IS NULL OR end_date >= $2::date)
          AND (
              $2::date > created_at::date
              OR (
                  $2::date = created_at::date
                  AND ($2::date + time_to_take) >= created_at
              )
          )
    `;

    const today_activity_summary_query = `
        SELECT
            COUNT(*) FILTER (
                WHERE UPPER(status) = ANY($2::text[])
            )::int AS completed_count,
            COUNT(*) FILTER (
                WHERE UPPER(status) = ANY($3::text[])
            )::int AS missed_count
        FROM activities
        WHERE patient_id = $1
          AND sche_time::date = $4::date
    `;

    const total_scheduled_result = await pool.query(total_scheduled_query, [
        patient_id,
        today_date_string
    ]);

    const today_activity_summary_result = await pool.query(today_activity_summary_query, [
        patient_id,
        COMPLETED_STATUSES,
        MISSED_STATUSES,
        today_date_string
    ]);

    const total_scheduled_count = total_scheduled_result.rows[0]?.count || 0;
    const completed_count = today_activity_summary_result.rows[0]?.completed_count || 0;
    const missed_count = today_activity_summary_result.rows[0]?.missed_count || 0;
    const today_remaining_count = Math.max(total_scheduled_count - completed_count, 0);

    const today_success_rate = total_scheduled_count > 0
        ? Math.round((completed_count / total_scheduled_count) * 100)
        : 0;

    const summary_status = getSummaryStatus(today_success_rate);

    return {
        today_success_rate,
        today_total_scheduled_count: total_scheduled_count,
        today_completed_count: completed_count,
        today_missed_count: missed_count,
        today_remaining_count,
        status_color: summary_status.color,
        status_message: summary_status.message
    };
};

const get_total_planned_schedule_count = async (patient_id) => {
    const query = `
        SELECT
            sche_id,
            start_date,
            end_date,
            time_to_take,
            created_at,
            dose_interval
        FROM schedules
        WHERE patient_id = $1
          AND status = 'ACTIVE'
    `;

    const { rows } = await pool.query(query, [patient_id]);

    return rows.reduce((sum, schedule) => {
        const planned_result = get_planned_quantity_for_one_schedule(schedule);

        if (!planned_result.calculable) {
            return sum;
        }

        return sum + planned_result.planned_quantity;
    }, 0);
};

const get_remaining_planned_medication_count = async (patient_id) => {
    const total_planned_count = await get_total_planned_schedule_count(patient_id);
    const query = `
        SELECT COUNT(a.activity_id)::int AS completed_count
        FROM activities a
        INNER JOIN schedules s
            ON s.sche_id = a.sche_id
        WHERE a.patient_id = $1
          AND s.patient_id = $1
          AND s.status = 'ACTIVE'
          AND UPPER(a.status) = ANY($2::text[])
    `;

    const { rows } = await pool.query(query, [patient_id, COMPLETED_STATUSES]);
    const completed_count = rows[0]?.completed_count || 0;

    return Math.max(total_planned_count - completed_count, 0);
};

const get_next_schedule_time_today = async (patient_id) => {
    const { current_date, today_date_string } = get_today_context();

    const query = `
        SELECT
            sche_id,
            time_to_take
        FROM schedules
        WHERE patient_id = $1
          AND status = 'ACTIVE'
          AND start_date <= $2::date
          AND (end_date IS NULL OR end_date >= $2::date)
          AND (
              $2::date > created_at::date
              OR (
                  $2::date = created_at::date
                  AND ($2::date + time_to_take) >= created_at
              )
          )
        ORDER BY time_to_take ASC, sche_id ASC
    `;

    const { rows } = await pool.query(query, [patient_id, today_date_string]);

    for (const row of rows) {
        const schedule_date = buildScheduleTimestamp(row.time_to_take, current_date);

        if (schedule_date && schedule_date.getTime() >= current_date.getTime()) {
            return schedule_date.toISOString();
        }
    }

    return null;
};

const get_device_status = async (patient_id) => {
    const { current_date } = get_today_context();

    const device_query = `
        SELECT
            device_id,
            device_uid,
            patient_id,
            device_status,
            last_ping,
            registered_at,
            NULL::int AS medication_level
        FROM devices
        WHERE patient_id = $1
        LIMIT 1
    `;

    const device_result = await pool.query(device_query, [patient_id]);
    const device = device_result.rows[0] || null;

    if (!device) {
        return null;
    }

    const next_schedule_time = await get_next_schedule_time_today(patient_id);

    const is_connected = is_device_online(device.last_ping, current_date);
    const connection_status = is_connected ? 'connected' : 'disconnected';

    const medication_level = device.medication_level;
    const last_sync_time = device.last_ping || device.registered_at || null;

    let status_color = 'green';
    let status_message = 'Normal';
    let status_reason = 'Device is connected normally.';

    if (connection_status === 'disconnected') {
        status_color = 'red';
        status_message = 'Disconnected';
        status_reason = 'Device connection is not available.';
    } else {
        const warnings = [];

        if (
            medication_level !== null &&
            medication_level !== undefined &&
            Number(medication_level) <= LOW_MEDICATION_THRESHOLD
        ) {
            warnings.push('Low medication level');
        }

        if (last_sync_time) {
            const sync_diff = current_date.getTime() - new Date(last_sync_time).getTime();

            if (sync_diff >= TEN_MINUTES_IN_MS) {
                warnings.push('Sync delayed');
            }
        }

        if (warnings.length > 0) {
            status_color = 'orange';
            status_message = 'Warning';
            status_reason = warnings.join(', ');
        }
    }

    return {
        connection_status,
        is_connected,
        medication_level,
        last_sync_time,
        next_schedule_time,
        status_color,
        status_message,
        status_reason,
        device_id: device.device_id,
        device_uid: device.device_uid
    };
};

const get_today_schedules = async (patient_id) => {
    const { today_date_string } = get_today_context();

    const query = `
        SELECT
            s.sche_id,
            s.patient_id,
            s.medi_id,
            s.time_to_take,
            s.start_date,
            s.end_date,
            s.dose_interval,
            s.created_at,
            s.status AS schedule_status,
            m.medi_name,
            a.activity_id,
            a.status AS log_status,
            a.sche_time,
            a.actual_time
        FROM schedules s
        LEFT JOIN medications m
            ON s.medi_id = m.medi_id
        LEFT JOIN activities a
            ON a.sche_id = s.sche_id
           AND a.patient_id = s.patient_id
           AND a.sche_time::date = $2::date
        WHERE s.patient_id = $1
          AND s.status = 'ACTIVE'
          AND s.start_date <= $2::date
          AND (s.end_date IS NULL OR s.end_date >= $2::date)
          AND (
              $2::date > s.created_at::date
              OR (
                  $2::date = s.created_at::date
                  AND ($2::date + s.time_to_take) >= s.created_at
              )
          )
        ORDER BY s.time_to_take ASC, s.sche_id ASC, a.activity_id DESC
    `;

    const { rows } = await pool.query(query, [patient_id, today_date_string]);
    const schedule_map = new Map();

    for (const row of rows) {
        if (!schedule_map.has(row.sche_id)) {
            schedule_map.set(row.sche_id, {
                sche_id: row.sche_id,
                patient_id: row.patient_id,
                medi_id: row.medi_id,
                medi_name: row.medi_name,
                time_to_take: row.time_to_take,
                created_at: row.created_at,
                planned_date: today_date_string,
                status: 'Scheduled',
                status_color: 'gray',
                log_status: null,
                actual_time: null
            });
        }

        const current_item = schedule_map.get(row.sche_id);
        const log_status = row.log_status ? String(row.log_status).toUpperCase() : null;

        if (!log_status) {
            continue;
        }

        if (COMPLETED_STATUSES.includes(log_status)) {
            current_item.status = 'Completed';
            current_item.status_color = getScheduleStatusColor('Completed');
            current_item.log_status = row.log_status;
            current_item.actual_time = row.actual_time;
            continue;
        }

        if (current_item.status !== 'Completed' && MISSED_STATUSES.includes(log_status)) {
            current_item.status = 'Missed';
            current_item.status_color = getScheduleStatusColor('Missed');
            current_item.log_status = row.log_status;
            current_item.actual_time = row.actual_time;
        }
    }

    return Array.from(schedule_map.values()).map((item) => {
        if (!item.status_color) {
            item.status_color = getScheduleStatusColor(item.status);
        }

        return item;
    });
};

const get_recent_notifications = async (mem_id) => {
    const query = `
        SELECT
            noti_id,
            noti_title,
            noti_msg,
            is_received,
            noti_type,
            created_at
        FROM notifications
        WHERE mem_id = $1
        ORDER BY created_at DESC, noti_id DESC
        LIMIT 5
    `;

    const { rows } = await pool.query(query, [mem_id]);

    return rows;
};

const get_recent_activities = async (patient_id) => {
    const query = `
        SELECT
            a.activity_id,
            a.sche_id,
            a.sche_time,
            a.actual_time,
            a.status,
            a.created_at,
            s.medi_id,
            m.medi_name
        FROM activities a
        LEFT JOIN schedules s
            ON a.sche_id = s.sche_id
        LEFT JOIN medications m
            ON s.medi_id = m.medi_id
        WHERE a.patient_id = $1
        ORDER BY a.created_at DESC, a.activity_id DESC
        LIMIT 5
    `;

    const { rows } = await pool.query(query, [patient_id]);

    return rows;
};

module.exports = {
    get_dashboard_data_by_mem_id
};
