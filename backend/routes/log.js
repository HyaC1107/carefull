const express = require('express');
const router = express.Router();

const pool = require('../db');
const { verifyToken } = require('../middleware/auth');
const { findUserIdByMemberId } = require('../utils/auth-user');
const { sendSuccess, sendError } = require('../utils/response');
const { parseNumericFields, parseNumericValue } = require('../utils/validators');

/**
 * 로그 저장 시 허용할 상태값 목록
 *
 * 왜 이렇게 두는가:
 * - logs.status는 통계/알림/복약 판정에 직접 쓰일 핵심 값이므로
 *   아무 문자열이나 들어가면 나중에 집계가 꼬일 수 있습니다.
 * - 현재 1차 구현 기준으로 SUCCESS / FAILED / MISSED만 허용합니다.
 */
const ALLOWED_LOG_STATUSES = ['SUCCESS', 'FAILED', 'MISSED'];

/**
 * SUCCESS 알림을 생성합니다.
 *
 * 왜 이렇게 두는가:
 * - MISSED 알림은 job이 자동 생성합니다.
 * - SUCCESS 알림은 실제 성공 로그가 들어온 시점에 생성하는 것이 자연스럽습니다.
 * - 기존 MISSED 알림은 "한 번 놓쳤던 이력"으로 그대로 유지합니다.
 */
const createSuccessNotification = async (client, memberId, logId, scheduleId) => {
    const medicationQuery = `
        SELECT
            m.name AS medication_name
        FROM schedules s
        INNER JOIN medications m
            ON s.medication_id = m.medication_id
        WHERE s.schedule_id = $1
        LIMIT 1
    `;

    const medicationResult = await client.query(medicationQuery, [scheduleId]);

    const medicationName = medicationResult.rows.length > 0
        ? medicationResult.rows[0].medication_name
        : '등록된 약';

    const title = '복약 완료 알림';
    const message = `${medicationName} 복약이 정상적으로 확인되었습니다.`;

    const insertNotificationQuery = `
        INSERT INTO notifications (
            member_id,
            log_id,
            title,
            message,
            is_read,
            type
        )
        VALUES ($1, $2, $3, $4, FALSE, 'SUCCESS')
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

    const { rows } = await client.query(insertNotificationQuery, [
        memberId,
        logId,
        title,
        message
    ]);

    return rows[0];
};

/**
 * POST /api/log
 * 로그인한 사용자의 환자(user_id) 기준으로 복약 로그를 저장합니다.
 *
 * 요청 body 예시:
 * {
 *   "schedule_id": 1,
 *   "planned_time": "2026-04-14T08:00:00+09:00",
 *   "actual_time": "2026-04-14T08:03:12+09:00",
 *   "status": "SUCCESS",
 *   "face_auth_result": true,
 *   "action_auth_result": true,
 *   "similarity_score": 0.9321
 * }
 */
router.post('/', verifyToken, async (req, res) => {
    const memberId = req.user.memberId;

    const {
        planned_time,
        actual_time,
        status,
        face_auth_result,
        action_auth_result
    } = req.body;

    if (!planned_time) {
        return sendError(res, 400, 'planned_time은 필수입니다.');
    }

    if (!status || !String(status).trim()) {
        return sendError(res, 400, 'status는 필수입니다.');
    }

    const numericFields = parseNumericFields(req.body, ['schedule_id']);
    if (!numericFields) {
        return sendError(res, 400, 'schedule_id는 숫자여야 합니다.');
    }

    const { schedule_id: parsedScheduleId } = numericFields;

    let parsedSimilarityScore = null;

    if (
        req.body.similarity_score !== undefined &&
        req.body.similarity_score !== null &&
        req.body.similarity_score !== ''
    ) {
        parsedSimilarityScore = parseNumericValue(req.body.similarity_score);

        if (parsedSimilarityScore === null) {
            return sendError(res, 400, 'similarity_score는 숫자여야 합니다.');
        }
    }

    const normalizedStatus = String(status).trim().toUpperCase();

    if (!ALLOWED_LOG_STATUSES.includes(normalizedStatus)) {
        return sendError(
            res,
            400,
            `status는 ${ALLOWED_LOG_STATUSES.join(', ')} 중 하나여야 합니다.`
        );
    }

    const client = await pool.connect();

    try {
        const userId = await findUserIdByMemberId(memberId);

        if (!userId) {
            return sendError(res, 404, '등록된 환자 정보가 없습니다.');
        }

        const scheduleCheckQuery = `
            SELECT
                schedule_id,
                user_id
            FROM schedules
            WHERE schedule_id = $1
              AND user_id = $2
            LIMIT 1
        `;

        const scheduleCheckResult = await client.query(scheduleCheckQuery, [
            parsedScheduleId,
            userId
        ]);

        if (scheduleCheckResult.rows.length === 0) {
            return sendError(res, 404, '해당 복약 일정이 없거나 접근 권한이 없습니다.');
        }

        await client.query('BEGIN');

        const insertQuery = `
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
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
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

        const logResult = await client.query(insertQuery, [
            userId,
            parsedScheduleId,
            planned_time,
            actual_time || null,
            normalizedStatus,
            face_auth_result ?? false,
            action_auth_result ?? false,
            parsedSimilarityScore
        ]);

        const insertedLog = logResult.rows[0];
        let createdNotification = null;

        // SUCCESS 로그면 복약 완료 알림도 함께 생성
        if (normalizedStatus === 'SUCCESS') {
            createdNotification = await createSuccessNotification(
                client,
                memberId,
                insertedLog.log_id,
                parsedScheduleId
            );
        }

        await client.query('COMMIT');

        return sendSuccess(res, 201, {
            message: '복약 로그가 저장되었습니다.',
            log: insertedLog,
            notification: createdNotification
        });
    } catch (error) {
        await client.query('ROLLBACK');
        console.error('복약 로그 저장 중 오류가 발생했습니다:', error);
        return sendError(res, 500, '복약 로그 저장 중 서버 오류가 발생했습니다.');
    } finally {
        client.release();
    }
});

/**
 * GET /api/log
 * 로그인한 사용자의 환자(user_id) 기준으로 내 복약 로그 목록을 조회합니다.
 */
router.get('/', verifyToken, async (req, res) => {
    const memberId = req.user.memberId;

    try {
        const userId = await findUserIdByMemberId(memberId);

        if (!userId) {
            return sendError(res, 404, '등록된 환자 정보가 없습니다.');
        }

        const query = `
            SELECT
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
            FROM logs
            WHERE user_id = $1
            ORDER BY planned_time DESC NULLS LAST, log_id DESC
        `;

        const { rows } = await pool.query(query, [userId]);

        return sendSuccess(res, 200, {
            logs: rows
        });
    } catch (error) {
        console.error('복약 로그 조회 중 오류가 발생했습니다:', error);
        return sendError(res, 500, '복약 로그 조회 중 서버 오류가 발생했습니다.');
    }
});

module.exports = router;