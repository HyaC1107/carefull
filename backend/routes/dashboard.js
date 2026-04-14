const express = require('express');
const router = express.Router();

const pool = require('../db');
const { verifyToken } = require('../middleware/auth');
const { findUserIdByMemberId } = require('../utils/auth-user');
const { sendSuccess, sendError } = require('../utils/response');

/**
 * dashboard.js 역할
 *
 * 왜 필요한가:
 * - 대시보드는 사용자가 앱에 들어왔을 때 오늘 복약 진행 상황,
 *   기기 연결 상태, 오늘 일정, 최근 알림/복약 기록을 한 번에 확인하는 첫 화면입니다.
 * - 기존 구버전 dashboard 라우터는 :userId를 직접 받아 현재 프로젝트의
 *   인증 흐름(req.user.memberId)과 맞지 않아 폐기하고 새로 작성합니다.
 */

// 실제 status enum은 운영 DB 기준 재확인 필요
const COMPLETED_STATUSES = ['SUCCESS', 'COMPLETED', 'TAKEN'];
const MISSED_STATUSES = ['MISSED', 'FAILED'];

const getTodayDateString = () => {
    return new Date().toISOString().slice(0, 10);
};

const getProjectDayOfWeek = (date) => {
    const day = date.getDay();
    return day === 0 ? 7 : day;
};

const getDashboardSummary = async (userId) => {
    const now = new Date();
    const todayDateString = getTodayDateString();
    const todayDayOfWeek = getProjectDayOfWeek(now);

    const totalScheduledQuery = `
        SELECT COUNT(*)::int AS count
        FROM schedules
        WHERE user_id = $1
          AND status = 'ACTIVE'
          AND start_date <= $2::date
          AND (end_date IS NULL OR end_date >= $2::date)
          AND (
                CASE
                    WHEN days_of_week IS NULL THEN FALSE
                    ELSE $3 = ANY(days_of_week)
                END
          )
    `;

    const todayLogsSummaryQuery = `
        SELECT
            COUNT(*) FILTER (
                WHERE UPPER(status) = ANY($2::text[])
            )::int AS completed_count,
            COUNT(*) FILTER (
                WHERE UPPER(status) = ANY($3::text[])
            )::int AS missed_count
        FROM logs
        WHERE user_id = $1
          AND planned_time::date = $4::date
    `;

    const totalScheduledResult = await pool.query(totalScheduledQuery, [
        userId,
        todayDateString,
        todayDayOfWeek
    ]);

    const todayLogsSummaryResult = await pool.query(todayLogsSummaryQuery, [
        userId,
        COMPLETED_STATUSES,
        MISSED_STATUSES,
        todayDateString
    ]);

    const totalScheduledCount = totalScheduledResult.rows[0]?.count || 0;
    const completedCount = todayLogsSummaryResult.rows[0]?.completed_count || 0;
    const missedCount = todayLogsSummaryResult.rows[0]?.missed_count || 0;

    const successRate = totalScheduledCount > 0
        ? Math.round((completedCount / totalScheduledCount) * 100)
        : 0;

    return {
        todaySuccessRate: successRate,
        todayTotalScheduledCount: totalScheduledCount,
        todayCompletedCount: completedCount,
        todayMissedCount: missedCount
    };
};

const getDeviceStatus = async (userId) => {
    // 실제 스키마 컬럼명 확인 필요: battery_level, fill_level, remaining_count, last_sync_at 등
    const deviceQuery = `
        SELECT
            device_id,
            serial_number,
            user_id,
            status,
            last_ping,
            registered_at,
            created_at
        FROM devices
        WHERE user_id = $1
        LIMIT 1
    `;

    const nextScheduleQuery = `
        SELECT
            schedule_id,
            scheduled_time
        FROM schedules
        WHERE user_id = $1
          AND status = 'ACTIVE'
        ORDER BY scheduled_time ASC, schedule_id ASC
        LIMIT 1
    `;

    const deviceResult = await pool.query(deviceQuery, [userId]);
    const nextScheduleResult = await pool.query(nextScheduleQuery, [userId]);

    const device = deviceResult.rows[0] || null;
    const nextSchedule = nextScheduleResult.rows[0] || null;

    if (!device) {
        return {
            isConnected: false,
            deviceId: null,
            serialNumber: null,
            deviceStatus: 'UNREGISTERED',
            fillLevel: null,
            remainingCount: null,
            lastSyncAt: null,
            nextScheduledTime: nextSchedule ? nextSchedule.scheduled_time : null
        };
    }

    return {
        isConnected: device.status === 'REGISTERED',
        deviceId: device.device_id,
        serialNumber: device.serial_number,
        deviceStatus: device.status,
        fillLevel: null,
        remainingCount: null,
        lastSyncAt: device.last_ping || device.registered_at || device.created_at || null,
        nextScheduledTime: nextSchedule ? nextSchedule.scheduled_time : null
    };
};

const getTodaySchedules = async (userId) => {
    const now = new Date();
    const todayDateString = getTodayDateString();
    const todayDayOfWeek = getProjectDayOfWeek(now);

    const query = `
        SELECT
            s.schedule_id,
            s.user_id,
            s.medication_id,
            s.dosage_count,
            s.scheduled_time,
            s.start_date,
            s.end_date,
            s.days_of_week,
            s.repeat_interval,
            s.status AS schedule_status,
            m.name AS medication_name,
            l.log_id,
            l.status AS log_status,
            l.planned_time,
            l.actual_time
        FROM schedules s
        LEFT JOIN medications m
            ON s.medication_id = m.medication_id
        LEFT JOIN logs l
            ON l.schedule_id = s.schedule_id
           AND l.user_id = s.user_id
           AND l.planned_time::date = $2::date
        WHERE s.user_id = $1
          AND s.status = 'ACTIVE'
          AND s.start_date <= $2::date
          AND (s.end_date IS NULL OR s.end_date >= $2::date)
          AND (
                CASE
                    WHEN s.days_of_week IS NULL THEN FALSE
                    ELSE $3 = ANY(s.days_of_week)
                END
          )
        ORDER BY s.scheduled_time ASC, s.schedule_id ASC, l.log_id DESC
    `;

    const { rows } = await pool.query(query, [userId, todayDateString, todayDayOfWeek]);
    const scheduleMap = new Map();

    for (const row of rows) {
        if (!scheduleMap.has(row.schedule_id)) {
            scheduleMap.set(row.schedule_id, {
                schedule_id: row.schedule_id,
                medication_id: row.medication_id,
                medication_name: row.medication_name,
                dosage_count: row.dosage_count,
                scheduled_time: row.scheduled_time,
                planned_date: todayDateString,
                status: '예정',
                log_status: null,
                actual_time: null
            });
        }

        const currentItem = scheduleMap.get(row.schedule_id);
        const logStatus = row.log_status ? String(row.log_status).toUpperCase() : null;

        if (!logStatus) {
            continue;
        }

        if (COMPLETED_STATUSES.includes(logStatus)) {
            currentItem.status = '완료';
            currentItem.log_status = row.log_status;
            currentItem.actual_time = row.actual_time;
            continue;
        }

        if (currentItem.status !== '완료' && MISSED_STATUSES.includes(logStatus)) {
            currentItem.status = '미복약';
            currentItem.log_status = row.log_status;
            currentItem.actual_time = row.actual_time;
        }
    }

    return Array.from(scheduleMap.values());
};

const getRecentNotifications = async (memberId) => {
    const query = `
        SELECT
            notification_id,
            title,
            message,
            is_read,
            type,
            created_at
        FROM notifications
        WHERE member_id = $1
        ORDER BY created_at DESC, notification_id DESC
        LIMIT 5
    `;

    const { rows } = await pool.query(query, [memberId]);
    return rows;
};

const getRecentLogs = async (userId) => {
    const query = `
        SELECT
            l.log_id,
            l.schedule_id,
            l.planned_time,
            l.actual_time,
            l.status,
            l.created_at,
            s.medication_id,
            s.dosage_count,
            m.name AS medication_name
        FROM logs l
        LEFT JOIN schedules s
            ON l.schedule_id = s.schedule_id
        LEFT JOIN medications m
            ON s.medication_id = m.medication_id
        WHERE l.user_id = $1
        ORDER BY l.created_at DESC, l.log_id DESC
        LIMIT 5
    `;

    const { rows } = await pool.query(query, [userId]);
    return rows;
};

router.get('/', verifyToken, async (req, res) => {
    const memberId = req.user.memberId;

    try {
        const userId = await findUserIdByMemberId(memberId);

        if (!userId) {
            return sendError(res, 404, '등록된 환자 정보가 없습니다.');
        }

        const [summary, device, todaySchedules, recentNotifications, recentLogs] = await Promise.all([
            getDashboardSummary(userId),
            getDeviceStatus(userId),
            getTodaySchedules(userId),
            getRecentNotifications(memberId),
            getRecentLogs(userId)
        ]);

        return sendSuccess(res, 200, {
            message: '대시보드 조회 성공',
            data: {
                summary,
                device,
                todaySchedules,
                recentNotifications,
                recentLogs
            }
        });
    } catch (error) {
        console.error('대시보드 조회 중 서버 오류가 발생했습니다:', error);
        return sendError(res, 500, '대시보드 조회 중 서버 오류가 발생했습니다.');
    }
});

module.exports = router;
