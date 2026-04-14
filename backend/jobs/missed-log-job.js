const pool = require('../db');

/**
 * 복약 실패 자동 판정 job 설정값
 *
 * 왜 이렇게 두는가:
 * - scheduled_time이 지나자마자 바로 미복약 처리하면 너무 빡빡할 수 있으므로
 *   일정 시간(유예시간) 이후에만 MISSED로 처리합니다.
 * - 현재 1차 구현에서는 30분 유예 후 미복약 처리합니다.
 */
const GRACE_MINUTES = 30;

/**
 * 오늘 날짜의 요일을 프로젝트 규칙(1=월 ~ 7=일)으로 구합니다.
 *
 * JavaScript getDay():
 * - 일 0 / 월 1 / 화 2 / 수 3 / 목 4 / 금 5 / 토 6
 *
 * 프로젝트 규칙:
 * - 월 1 / 화 2 / 수 3 / 목 4 / 금 5 / 토 6 / 일 7
 */
const getProjectDayOfWeek = (date) => {
    const day = date.getDay();
    return day === 0 ? 7 : day;
};

/**
 * HH:mm:ss 문자열을 Date 객체(오늘 날짜 기준)로 합쳐줍니다.
 */
const buildTodayDateTime = (timeString, now) => {
    const [hours = 0, minutes = 0, seconds = 0] = String(timeString)
        .split(':')
        .map(Number);

    const target = new Date(now);
    target.setHours(hours, minutes, seconds, 0);

    return target;
};

/**
 * 오늘 기준으로 "미복약 처리 후보" 스케줄을 조회합니다.
 */
const findActiveScheduleCandidates = async () => {
    const query = `
        SELECT
            s.schedule_id,
            s.user_id,
            s.medication_id,
            s.scheduled_time,
            s.start_date,
            s.end_date,
            s.days_of_week,
            s.repeat_interval,
            s.status,
            u.member_id,
            m.name AS medication_name
        FROM schedules s
        INNER JOIN users u
            ON s.user_id = u.user_id
        INNER JOIN medications m
            ON s.medication_id = m.medication_id
        WHERE s.status = 'ACTIVE'
        ORDER BY s.schedule_id
    `;

    const { rows } = await pool.query(query);
    return rows;
};

/**
 * 오늘 해당 schedule에 SUCCESS 로그가 이미 있는지 확인합니다.
 *
 * 왜 필요한가:
 * - 이미 복약 성공한 일정인데 job이 다시 미복약 처리하면 안 됩니다.
 */
const hasSuccessLogToday = async (scheduleId, userId, todayDateString) => {
    const query = `
        SELECT log_id
        FROM logs
        WHERE schedule_id = $1
          AND user_id = $2
          AND status = 'SUCCESS'
          AND planned_time::date = $3::date
        LIMIT 1
    `;

    const { rows } = await pool.query(query, [scheduleId, userId, todayDateString]);
    return rows.length > 0;
};

/**
 * 오늘 해당 schedule에 MISSED 로그가 이미 있는지 확인합니다.
 *
 * 왜 필요한가:
 * - 중복 실행으로 같은 일정에 MISSED 로그가 여러 번 쌓이는 걸 방지합니다.
 */
const hasMissedLogToday = async (scheduleId, userId, todayDateString) => {
    const query = `
        SELECT log_id
        FROM logs
        WHERE schedule_id = $1
          AND user_id = $2
          AND status = 'MISSED'
          AND planned_time::date = $3::date
        LIMIT 1
    `;

    const { rows } = await pool.query(query, [scheduleId, userId, todayDateString]);
    return rows.length > 0;
};

/**
 * MISSED 로그를 생성합니다.
 */
const insertMissedLog = async (client, target) => {
    const query = `
        INSERT INTO logs (
            user_id,
            schedule_id,
            planned_time,
            actual_time,
            status,
            face_auth_result,
            action_auth_result,
            similarity_score
        )
        VALUES ($1, $2, $3, NULL, 'MISSED', FALSE, FALSE, NULL)
        RETURNING
            log_id,
            user_id,
            schedule_id,
            planned_time,
            actual_time,
            status,
            face_auth_result,
            action_auth_result,
            similarity_score,
            created_at
    `;

    const { rows } = await client.query(query, [
        target.user_id,
        target.schedule_id,
        target.planned_time
    ]);

    return rows[0];
};

/**
 * MISSED 알림을 생성합니다.
 *
 * 왜 이렇게 두는가:
 * - 보호자 화면에서 바로 확인할 수 있도록 notifications 테이블에 기록합니다.
 * - 현재 1차 구현에서는 type을 'MISSED'로 고정합니다.
 */
const insertMissedNotification = async (client, target, logId) => {
    const title = '복약 실패 알림';
    const message = `${target.medication_name} 복약 시간이 지났지만 복약 기록이 확인되지 않았습니다.`;

    const query = `
        INSERT INTO notifications (
            member_id,
            log_id,
            title,
            message,
            is_read,
            type
        )
        VALUES ($1, $2, $3, $4, FALSE, 'MISSED')
        RETURNING
            notification_id,
            member_id,
            log_id,
            title,
            message,
            is_read,
            type,
            created_at
    `;

    const { rows } = await client.query(query, [
        target.member_id,
        logId,
        title,
        message
    ]);

    return rows[0];
};

/**
 * schedules 후보 중 실제로 미복약 처리해야 할 대상을 고릅니다.
 */
const filterMissedTargets = (candidates) => {
    const now = new Date();
    const todayDateString = now.toISOString().slice(0, 10);
    const todayDayOfWeek = getProjectDayOfWeek(now);

    return candidates
        .filter((item) => {
            const scheduleDays = Array.isArray(item.days_of_week) ? item.days_of_week : [];

            if (!scheduleDays.includes(todayDayOfWeek)) {
                return false;
            }

            const startDateString = item.start_date instanceof Date
                ? item.start_date.toISOString().slice(0, 10)
                : String(item.start_date).slice(0, 10);

            if (startDateString > todayDateString) {
                return false;
            }

            if (item.end_date) {
                const endDateString = item.end_date instanceof Date
                    ? item.end_date.toISOString().slice(0, 10)
                    : String(item.end_date).slice(0, 10);

                if (endDateString < todayDateString) {
                    return false;
                }
            }

            const plannedDateTime = buildTodayDateTime(item.scheduled_time, now);
            const deadlineDateTime = new Date(plannedDateTime.getTime() + GRACE_MINUTES * 60 * 1000);

            if (now < deadlineDateTime) {
                return false;
            }

            return true;
        })
        .map((item) => {
            const plannedDateTime = buildTodayDateTime(item.scheduled_time, now);

            return {
                ...item,
                planned_time: plannedDateTime
            };
        });
};

/**
 * 실제 미복약 체크를 1회 수행합니다.
 *
 * 동작 순서:
 * 1. ACTIVE 스케줄 후보 조회
 * 2. 오늘 날짜 + 요일 + 유예시간 기준으로 미복약 대상 선별
 * 3. SUCCESS 로그가 없고 MISSED 로그도 없는 대상만 처리
 * 4. logs에 MISSED 저장
 * 5. notifications에 보호자 알림 저장
 *
 * 주의:
 * - 나중에 SUCCESS 로그가 들어와도 기존 MISSED 알림은 유지합니다.
 * - 즉 "놓쳤던 이력"과 "나중에 복약 완료한 이력"을 모두 남기는 구조입니다.
 */
const runMissedLogJob = async () => {
    const client = await pool.connect();

    try {
        const now = new Date();
        const todayDateString = now.toISOString().slice(0, 10);

        const candidates = await findActiveScheduleCandidates();
        const targets = filterMissedTargets(candidates);

        if (targets.length === 0) {
            console.log('[MISSED-LOG-JOB] 처리 대상이 없습니다.');
            return;
        }

        for (const target of targets) {
            try {
                const alreadySuccess = await hasSuccessLogToday(
                    target.schedule_id,
                    target.user_id,
                    todayDateString
                );

                if (alreadySuccess) {
                    continue;
                }

                const alreadyMissed = await hasMissedLogToday(
                    target.schedule_id,
                    target.user_id,
                    todayDateString
                );

                if (alreadyMissed) {
                    continue;
                }

                await client.query('BEGIN');

                const insertedLog = await insertMissedLog(client, target);
                await insertMissedNotification(client, target, insertedLog.log_id);

                await client.query('COMMIT');

                console.log(
                    `[MISSED-LOG-JOB] MISSED 처리 완료 - schedule_id: ${target.schedule_id}, log_id: ${insertedLog.log_id}`
                );
            } catch (error) {
                await client.query('ROLLBACK');
                console.error('[MISSED-LOG-JOB] 개별 대상 처리 중 오류가 발생했습니다:', error);
            }
        }
    } catch (error) {
        console.error('[MISSED-LOG-JOB] 실행 중 오류가 발생했습니다:', error);
    } finally {
        client.release();
    }
};

/**
 * 미복약 자동 판정 job을 시작합니다.
 */
const startMissedLogJob = () => {
    console.log('[MISSED-LOG-JOB] 미복약 자동 판정 job을 시작합니다.');

    runMissedLogJob();

    setInterval(() => {
        runMissedLogJob();
    }, 60 * 1000);
};

module.exports = {
    startMissedLogJob,
    runMissedLogJob
};