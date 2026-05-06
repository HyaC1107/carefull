const pool = require('../db');
const { find_patient_id_by_mem_id } = require('../utils/auth-user');
const {
    COMPLETED_STATUSES,
    MISSED_STATUSES,
    TEN_MINUTES_IN_MS,
    LOW_MEDICATION_THRESHOLD,
    getKstDateString,
    getTodayDateString,
    getKstWallClockDate,
    buildKstDateTimeString,
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
    const current_date = getKstWallClockDate();

    return {
        current_date,
        today_date_string: getTodayDateString(),
        today_day_of_week: getProjectDayOfWeek(current_date)
    };
};

const measure_dashboard_step = async (step_name, callback) => {
    const started_at = Date.now();

    try {
        return await callback();
    } finally {
        console.info(`[dashboard] ${step_name}: ${Date.now() - started_at}ms`);
    }
};

const DAY_IN_MS = 24 * 60 * 60 * 1000;

const normalize_status = (status) => String(status || '').trim().toUpperCase();

const is_completed_status = (status) => COMPLETED_STATUSES.includes(normalize_status(status));
const is_missed_status = (status) => normalize_status(status) === 'MISSED';
const is_failed_status = (status) => ['FAILED', 'ERROR'].includes(normalize_status(status));

const parse_kst_date_string = (value) => {
    if (!value) return null;
    const text = value instanceof Date
        ? value.toISOString().slice(0, 10)
        : String(value).slice(0, 10);
    const [year, month, day] = text.split('-').map(Number);
    if (!year || !month || !day) return null;
    return new Date(Date.UTC(year, month - 1, day));
};

const format_kst_date_string = (date) => {
    if (!(date instanceof Date) || Number.isNaN(date.getTime())) return null;
    return date.toISOString().slice(0, 10);
};

const add_days = (date, days) => new Date(date.getTime() + days * DAY_IN_MS);

const get_month_key = (date_string) => String(date_string || '').slice(0, 7);

const get_recent_kst_month_buckets = (count = 6) => {
    const today = parse_kst_date_string(getTodayDateString());
    const buckets = [];

    for (let index = count - 1; index >= 0; index -= 1) {
        const month_date = new Date(Date.UTC(
            today.getUTCFullYear(),
            today.getUTCMonth() - index,
            1
        ));
        const key = format_kst_date_string(month_date).slice(0, 7);
        buckets.push({
            key,
            month: `${month_date.getUTCMonth() + 1}월`,
            planned_count: 0,
            success_count: 0,
            missed_count: 0,
            failed_count: 0,
            success_rate: 0
        });
    }

    return buckets;
};

const get_stats_range = () => {
    const months = get_recent_kst_month_buckets(6);
    return {
        start_date: `${months[0].key}-01`,
        end_date: getTodayDateString(),
        months
    };
};

const should_include_schedule_instance = (schedule, date_string) => {
    const schedule_date = parse_kst_date_string(date_string);
    const start_date = parse_kst_date_string(schedule.start_date);
    if (!schedule_date || !start_date) return false;

    const step_days = Number.isInteger(Number(schedule.dose_interval)) && Number(schedule.dose_interval) > 0
        ? Number(schedule.dose_interval)
        : 1;
    const diff_days = Math.floor((schedule_date.getTime() - start_date.getTime()) / DAY_IN_MS);

    if (diff_days < 0 || diff_days % step_days !== 0) return false;

    if (!schedule.created_at) return true;

    const planned_at = new Date(`${date_string}T${String(schedule.time_to_take || '00:00:00')}+09:00`);
    const created_at = new Date(schedule.created_at);

    if (Number.isNaN(planned_at.getTime()) || Number.isNaN(created_at.getTime())) {
        return true;
    }

    return planned_at.getTime() >= created_at.getTime();
};

const get_activity_date_key = (activity) => {
    if (!activity?.sche_time) return null;
    return getKstDateString(activity.sche_time);
};

const rank_activity_status = (status) => {
    if (is_completed_status(status)) return 3;
    if (is_failed_status(status)) return 2;
    if (is_missed_status(status)) return 1;
    return 0;
};

const build_activity_lookup = (activities) => {
    const lookup = new Map();

    for (const activity of activities) {
        const date_key = get_activity_date_key(activity);
        if (!date_key || !activity.sche_id) continue;

        const key = `${activity.sche_id}:${date_key}`;
        const current = lookup.get(key);

        if (
            !current ||
            rank_activity_status(activity.status) > rank_activity_status(current.status) ||
            (
                rank_activity_status(activity.status) === rank_activity_status(current.status) &&
                Number(activity.activity_id || 0) > Number(current.activity_id || 0)
            )
        ) {
            lookup.set(key, activity);
        }
    }

    return lookup;
};

const get_dashboard_statistics = async (patient_id) => {
    const { start_date, end_date, months } = get_stats_range();
    const weekly_start_date = format_kst_date_string(
        add_days(parse_kst_date_string(end_date), -6)
    );

    const schedules_query = `
        SELECT
            s.sche_id,
            s.patient_id,
            s.medi_id,
            s.time_to_take,
            s.start_date,
            s.end_date,
            s.dose_interval,
            s.created_at,
            m.medi_name
        FROM schedules s
        LEFT JOIN medications m
            ON m.medi_id = s.medi_id
        WHERE s.patient_id = $1
          AND s.status = 'ACTIVE'
          AND s.start_date <= $3::date
          AND (s.end_date IS NULL OR s.end_date >= $2::date)
    `;

    const activities_query = `
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
            ON s.sche_id = a.sche_id
        LEFT JOIN medications m
            ON m.medi_id = s.medi_id
        WHERE a.patient_id = $1
          AND (a.sche_time AT TIME ZONE 'Asia/Seoul')::date >= $2::date
          AND (a.sche_time AT TIME ZONE 'Asia/Seoul')::date <= $3::date
    `;

    const [{ rows: schedules }, { rows: activities }] = await Promise.all([
        pool.query(schedules_query, [patient_id, start_date, end_date]),
        pool.query(activities_query, [patient_id, start_date, end_date])
    ]);

    const activity_lookup = build_activity_lookup(activities);
    const month_map = new Map(months.map((item) => [item.key, { ...item }]));
    const medication_map = new Map();
    const weekly = {
        planned_count: 0,
        success_count: 0,
        missed_count: 0,
        failed_count: 0,
        success_rate: 0
    };

    const range_start = parse_kst_date_string(start_date);
    const range_end = parse_kst_date_string(end_date);

    for (const schedule of schedules) {
        const schedule_start = parse_kst_date_string(schedule.start_date);
        const schedule_end = schedule.end_date
            ? parse_kst_date_string(schedule.end_date)
            : range_end;
        if (!schedule_start || !schedule_end) continue;

        let cursor = schedule_start.getTime() > range_start.getTime()
            ? schedule_start
            : range_start;
        const final_date = schedule_end.getTime() < range_end.getTime()
            ? schedule_end
            : range_end;

        while (cursor.getTime() <= final_date.getTime()) {
            const planned_date = format_kst_date_string(cursor);
            cursor = add_days(cursor, 1);

            if (!should_include_schedule_instance(schedule, planned_date)) continue;

            const activity = activity_lookup.get(`${schedule.sche_id}:${planned_date}`);
            const completed = activity && is_completed_status(activity.status);
            const failed = activity && is_failed_status(activity.status);
            const missed = !completed && !failed;
            const month_key = get_month_key(planned_date);
            const month_bucket = month_map.get(month_key);

            if (month_bucket) {
                month_bucket.planned_count += 1;
                if (completed) month_bucket.success_count += 1;
                else if (failed) month_bucket.failed_count += 1;
                if (missed) month_bucket.missed_count += 1;
            }

            const medication_key = String(schedule.medi_id);
            if (!medication_map.has(medication_key)) {
                medication_map.set(medication_key, {
                    medi_id: schedule.medi_id,
                    medi_name: schedule.medi_name || null,
                    planned_count: 0,
                    success_count: 0,
                    missed_count: 0,
                    failed_count: 0,
                    success_rate: 0
                });
            }
            const medication_stat = medication_map.get(medication_key);
            medication_stat.planned_count += 1;
            if (completed) medication_stat.success_count += 1;
            else if (failed) medication_stat.failed_count += 1;
            if (missed) medication_stat.missed_count += 1;

            if (planned_date >= weekly_start_date && planned_date <= end_date) {
                weekly.planned_count += 1;
                if (completed) weekly.success_count += 1;
                else if (failed) weekly.failed_count += 1;
                if (missed) weekly.missed_count += 1;
            }
        }
    }

    const monthly_trend = Array.from(month_map.values()).map((item) => ({
        ...item,
        success_rate: item.planned_count > 0
            ? Math.round((item.success_count / item.planned_count) * 100)
            : 0,
        missed_rate: item.planned_count > 0
            ? Math.round(((item.missed_count + item.failed_count) / item.planned_count) * 100)
            : 0
    }));

    const medication_rates = Array.from(medication_map.values())
        .map((item) => ({
            ...item,
            success_rate: item.planned_count > 0
                ? Math.round((item.success_count / item.planned_count) * 100)
                : 0
        }))
        .sort((a, b) =>
            b.planned_count - a.planned_count ||
            a.success_rate - b.success_rate ||
            String(a.medi_name || '').localeCompare(String(b.medi_name || ''))
        )
        .slice(0, 5);

    weekly.success_rate = weekly.planned_count > 0
        ? Math.round((weekly.success_count / weekly.planned_count) * 100)
        : 0;

    return {
        range: {
            start_date,
            end_date,
            timezone: 'Asia/Seoul'
        },
        completed_statuses: COMPLETED_STATUSES,
        missed_statuses: MISSED_STATUSES,
        monthly_trend,
        medication_rates,
        weekly
    };
};

const get_dashboard_data_by_mem_id = async (mem_id) => {
    const total_started_at = Date.now();

    try {
        const member = await measure_dashboard_step('get_member_header', () =>
            get_member_header(mem_id)
        );

        if (!member) {
            return null;
        }

        const patient_id = await measure_dashboard_step('find_patient_id_by_mem_id', () =>
            find_patient_id_by_mem_id(mem_id)
        );

        if (!patient_id) {
            const dashboard_data = build_dashboard_data({
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
                recent_notifications: await measure_dashboard_step('recent_notifications', () =>
                    get_recent_notifications(mem_id)
                ),
                recent_activities: [],
                statistics: {
                    range: {
                        start_date: get_stats_range().start_date,
                        end_date: get_stats_range().end_date,
                        timezone: 'Asia/Seoul'
                    },
                    completed_statuses: COMPLETED_STATUSES,
                    missed_statuses: MISSED_STATUSES,
                    monthly_trend: [],
                    medication_rates: [],
                    weekly: {
                        planned_count: 0,
                        success_count: 0,
                        missed_count: 0,
                        failed_count: 0,
                        success_rate: 0
                    }
                }
            });

            return dashboard_data;
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
            recent_activities,
            statistics
        ] = await Promise.all([
            measure_dashboard_step('get_patient_header', () => get_patient_header(patient_id)),
            measure_dashboard_step('get_dashboard_summary', () =>
                get_dashboard_summary(patient_id)
            ),
            measure_dashboard_step('total_scheduled_count', () =>
                get_total_planned_schedule_count(patient_id)
            ),
            measure_dashboard_step('remaining_medication_count', () =>
                get_remaining_planned_medication_count(patient_id)
            ),
            measure_dashboard_step('get_device_status', () => get_device_status(patient_id)),
            measure_dashboard_step('get_estimated_medication_stock', () =>
                get_estimated_medication_stock(patient_id)
            ),
            measure_dashboard_step('get_today_schedules', () =>
                get_today_schedules(patient_id)
            ),
            measure_dashboard_step('recent_notifications', () =>
                get_recent_notifications(mem_id)
            ),
            measure_dashboard_step('recent_activities', () =>
                get_recent_activities(patient_id)
            ),
            measure_dashboard_step('get_dashboard_statistics', () =>
                get_dashboard_statistics(patient_id)
            )
        ]);

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
            recent_activities,
            statistics
        });

        return dashboard_data;
    } finally {
        console.info(`[dashboard] total: ${Date.now() - total_started_at}ms`);
    }
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
    recent_activities,
    statistics
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
        recent_activities,
        statistics
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
              $2::date > (created_at AT TIME ZONE 'Asia/Seoul')::date
              OR (
                  $2::date = (created_at AT TIME ZONE 'Asia/Seoul')::date
                  AND ($2::date + time_to_take) >= (created_at AT TIME ZONE 'Asia/Seoul')
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
          AND (sche_time AT TIME ZONE 'Asia/Seoul')::date = $4::date
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
              $2::date > (created_at AT TIME ZONE 'Asia/Seoul')::date
              OR (
                  $2::date = (created_at AT TIME ZONE 'Asia/Seoul')::date
                  AND ($2::date + time_to_take) >= (created_at AT TIME ZONE 'Asia/Seoul')
              )
          )
        ORDER BY time_to_take ASC, sche_id ASC
    `;

    const { rows } = await pool.query(query, [patient_id, today_date_string]);

    for (const row of rows) {
        const schedule_date = buildScheduleTimestamp(row.time_to_take, current_date);

        if (schedule_date && schedule_date.getTime() >= current_date.getTime()) {
            return buildKstDateTimeString(new Date(), row.time_to_take);
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

    const is_connected = is_device_online(device.last_ping);
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
           AND (a.sche_time AT TIME ZONE 'Asia/Seoul')::date = $2::date
        WHERE s.patient_id = $1
          AND s.status = 'ACTIVE'
          AND s.start_date <= $2::date
          AND (s.end_date IS NULL OR s.end_date >= $2::date)
          AND (
              $2::date > (s.created_at AT TIME ZONE 'Asia/Seoul')::date
              OR (
                  $2::date = (s.created_at AT TIME ZONE 'Asia/Seoul')::date
                  AND ($2::date + s.time_to_take) >= (s.created_at AT TIME ZONE 'Asia/Seoul')
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
