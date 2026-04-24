const pool = require('../db');
const { ACTIVITY_STATUS } = require('../utils/activity-status');
const {
    NOTIFICATION_TYPE,
    trigger_activity_notification_safe
} = require('../services/notification-trigger.service');

const GRACE_MINUTES = 30;
const JOB_INTERVAL_MS = 60 * 1000;

const getProjectDayOfWeek = (date) => {
    const day = date.getDay();
    return day === 0 ? 7 : day;
};

const buildTodayDateTime = (time_string, now) => {
    const [hours = 0, minutes = 0, seconds = 0] = String(time_string)
        .split(':')
        .map(Number);

    const target = new Date(now);
    target.setHours(hours, minutes, seconds, 0);

    return target;
};

const findActiveScheduleCandidates = async () => {
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
            p.mem_id,
            m.medi_name
        FROM schedules s
        INNER JOIN patients p
            ON s.patient_id = p.patient_id
        INNER JOIN medications m
            ON s.medi_id = m.medi_id
        WHERE s.status = 'ACTIVE'
        ORDER BY s.sche_id
    `;

    const { rows } = await pool.query(query);
    return rows;
};

const hasAnyActivityForScheduleTime = async (sche_id, patient_id, today_date_string) => {
    const query = `
        SELECT
            activity_id,
            status
        FROM activities
        WHERE sche_id = $1
          AND patient_id = $2
          AND sche_time::date = $3::date
        LIMIT 1
    `;

    const { rows } = await pool.query(query, [sche_id, patient_id, today_date_string]);
    return rows[0] || null;
};

const insertMissedActivity = async (client, target) => {
    const query = `
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
        VALUES ($1, $2, $3, NULL, $4, FALSE, FALSE, 0)
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

    const { rows } = await client.query(query, [
        target.patient_id,
        target.sche_id,
        target.sche_time,
        ACTIVITY_STATUS.MISSED
    ]);

    return rows[0];
};

const filterMissedTargets = (candidates) => {
    const now = new Date();
    const today_date_string = now.toISOString().slice(0, 10);
    return candidates
        .filter((item) => {
            const start_date_string = item.start_date instanceof Date
                ? item.start_date.toISOString().slice(0, 10)
                : String(item.start_date).slice(0, 10);

            if (start_date_string > today_date_string) {
                return false;
            }

            if (item.end_date) {
                const end_date_string = item.end_date instanceof Date
                    ? item.end_date.toISOString().slice(0, 10)
                    : String(item.end_date).slice(0, 10);

                if (end_date_string < today_date_string) {
                    return false;
                }
            }

            const planned_date_time = buildTodayDateTime(item.time_to_take, now);
            const deadline_date_time = new Date(planned_date_time.getTime() + GRACE_MINUTES * 60 * 1000);

            if (now < deadline_date_time) {
                return false;
            }

            return true;
        })
        .map((item) => {
            const planned_date_time = buildTodayDateTime(item.time_to_take, now);

            return {
                ...item,
                sche_time: planned_date_time
            };
        });
};

const runMissedLogJob = async () => {
    const client = await pool.connect();

    try {
        const now = new Date();
        const today_date_string = now.toISOString().slice(0, 10);

        const candidates = await findActiveScheduleCandidates();
        const targets = filterMissedTargets(candidates);

        if (targets.length === 0) {
            console.log('[MISSED-ACTIVITY-JOB] no targets to process.');
            return;
        }

        for (const target of targets) {
            try {
                const existing_activity = await hasAnyActivityForScheduleTime(
                    target.sche_id,
                    target.patient_id,
                    today_date_string
                );

                // SUCCESS / FAILED / ERROR / MISSED 중 무엇이든 이미 있으면 자동 MISSED를 만들지 않는다.
                if (existing_activity) {
                    continue;
                }

                await client.query('BEGIN');

                const inserted_activity = await insertMissedActivity(client, target);

                await client.query('COMMIT');

                // 미복약 로그는 남기고, 알림은 별도 안전 호출로 분리한다.
                await trigger_activity_notification_safe({
                    mem_id: target.mem_id,
                    patient_id: target.patient_id,
                    activity_id: inserted_activity.activity_id,
                    event_type: NOTIFICATION_TYPE.MISSED,
                    medi_name: target.medi_name || '등록된 약'
                });

                console.log(
                    `[MISSED-ACTIVITY-JOB] processed - sche_id: ${target.sche_id}, activity_id: ${inserted_activity.activity_id}`
                );
            } catch (error) {
                await client.query('ROLLBACK');
                console.error('[MISSED-ACTIVITY-JOB] target processing error:', error);
            }
        }
    } catch (error) {
        console.error('[MISSED-ACTIVITY-JOB] run error:', error);
    } finally {
        client.release();
    }
};

const startMissedLogJob = () => {
    console.log('[MISSED-ACTIVITY-JOB] started.');

    runMissedLogJob();

    setInterval(() => {
        runMissedLogJob();
    }, JOB_INTERVAL_MS);
};

module.exports = {
    startMissedLogJob,
    runMissedLogJob
};
