const express = require('express');
const router = express.Router();

const pool = require('../db');
const { verifyToken } = require('../middleware/auth');
const { findUserIdByMemberId } = require('../utils/auth-user');
const { parseNumericFields, parseNumericValue, validateRequiredFields } = require('../utils/validators');
const { sendSuccess, sendError } = require('../utils/response');

/**
 * 일정 생성/수정 시 필수 필드를 검증합니다.
 *
 * 왜 이렇게 두는가:
 * - 기존 schedule API의 필수값 의미는 유지해야 하므로
 *   schedule.js 전용 규칙은 남겨둡니다.
 * - 다만 실제 검증 동작은 utils/validators.js의 공통 함수로 위임합니다.
 */
const validateSchedulePayload = (body) => {
    const requiredFields = [
        'medication_id',
        'dosage_count',
        'scheduled_time',
        'start_date',
        'end_date',
        'days_of_week',
        'repeat_interval',
        'status'
    ];

    return validateRequiredFields(body, requiredFields);
};

/**
 * POST /api/schedule
 * 로그인한 사용자의 환자(user_id) 기준으로 새 복약 일정을 등록합니다.
 */
router.post('/', verifyToken, async (req, res) => {
    const memberId = req.user.memberId;

    const validationError = validateSchedulePayload(req.body);
    if (validationError) {
        return sendError(res, 400, validationError);
    }

    const {
        scheduled_time,
        start_date,
        end_date,
        days_of_week,
        status
    } = req.body;

    const numericFields = parseNumericFields(req.body, [
        'medication_id',
        'dosage_count',
        'repeat_interval'
    ]);

    if (!numericFields) {
        return sendError(res, 400, 'medication_id, dosage_count, repeat_interval은 숫자여야 합니다.');
    }

    const {
        medication_id: parsedMedicationId,
        dosage_count: parsedDosageCount,
        repeat_interval: parsedRepeatInterval
    } = numericFields;

    try {
        const userId = await findUserIdByMemberId(memberId);

        if (!userId) {
            return sendError(res, 404, '등록된 환자 정보가 없습니다. 먼저 환자 등록을 완료해야 합니다.');
        }

        const insertQuery = `
            INSERT INTO schedules (
                user_id,
                medication_id,
                dosage_count,
                scheduled_time,
                start_date,
                end_date,
                days_of_week,
                repeat_interval,
                status
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            RETURNING
                schedule_id,
                user_id,
                medication_id,
                dosage_count,
                scheduled_time,
                start_date,
                end_date,
                days_of_week,
                repeat_interval,
                status
        `;

        const { rows } = await pool.query(insertQuery, [
            userId,
            parsedMedicationId,
            parsedDosageCount,
            scheduled_time,
            start_date,
            end_date,
            days_of_week,
            parsedRepeatInterval,
            status
        ]);

        return sendSuccess(res, 201, {
            message: '복약 일정이 등록되었습니다.',
            schedule: rows[0]
        });
    } catch (error) {
        console.error('복약 일정 등록 중 오류가 발생했습니다:', error);
        return sendError(res, 500, '복약 일정 등록 중 서버 오류가 발생했습니다.');
    }
});

/**
 * GET /api/schedule
 * 로그인한 사용자의 환자(user_id) 기준으로 내 일정 목록을 조회합니다.
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
                schedule_id,
                user_id,
                medication_id,
                dosage_count,
                scheduled_time,
                start_date,
                end_date,
                days_of_week,
                repeat_interval,
                status
            FROM schedules
            WHERE user_id = $1
            ORDER BY start_date, scheduled_time, schedule_id
        `;

        const { rows } = await pool.query(query, [userId]);

        return sendSuccess(res, 200, {
            schedules: rows
        });
    } catch (error) {
        console.error('복약 일정 조회 중 오류가 발생했습니다:', error);
        return sendError(res, 500, '복약 일정 조회 중 서버 오류가 발생했습니다.');
    }
});

/**
 * PUT /api/schedule/:id
 * 로그인한 사용자의 환자(user_id)에 속한 일정만 수정합니다.
 */
router.put('/:id', verifyToken, async (req, res) => {
    const memberId = req.user.memberId;
    const parsedScheduleId = parseNumericValue(req.params.id);

    if (parsedScheduleId === null) {
        return sendError(res, 400, '유효하지 않은 schedule id입니다.');
    }

    const validationError = validateSchedulePayload(req.body);
    if (validationError) {
        return sendError(res, 400, validationError);
    }

    const {
        scheduled_time,
        start_date,
        end_date,
        days_of_week,
        status
    } = req.body;

    const numericFields = parseNumericFields(req.body, [
        'medication_id',
        'dosage_count',
        'repeat_interval'
    ]);

    if (!numericFields) {
        return sendError(res, 400, 'medication_id, dosage_count, repeat_interval은 숫자여야 합니다.');
    }

    const {
        medication_id: parsedMedicationId,
        dosage_count: parsedDosageCount,
        repeat_interval: parsedRepeatInterval
    } = numericFields;

    try {
        const userId = await findUserIdByMemberId(memberId);

        if (!userId) {
            return sendError(res, 404, '등록된 환자 정보가 없습니다.');
        }

        const updateQuery = `
            UPDATE schedules
            SET
                medication_id = $1,
                dosage_count = $2,
                scheduled_time = $3,
                start_date = $4,
                end_date = $5,
                days_of_week = $6,
                repeat_interval = $7,
                status = $8
            WHERE schedule_id = $9
              AND user_id = $10
            RETURNING
                schedule_id,
                user_id,
                medication_id,
                dosage_count,
                scheduled_time,
                start_date,
                end_date,
                days_of_week,
                repeat_interval,
                status
        `;

        const { rows } = await pool.query(updateQuery, [
            parsedMedicationId,
            parsedDosageCount,
            scheduled_time,
            start_date,
            end_date,
            days_of_week,
            parsedRepeatInterval,
            status,
            parsedScheduleId,
            userId
        ]);

        if (rows.length === 0) {
            return sendError(res, 404, '수정할 복약 일정이 없거나 접근 권한이 없습니다.');
        }

        return sendSuccess(res, 200, {
            message: '복약 일정이 수정되었습니다.',
            schedule: rows[0]
        });
    } catch (error) {
        console.error('복약 일정 수정 중 오류가 발생했습니다:', error);
        return sendError(res, 500, '복약 일정 수정 중 서버 오류가 발생했습니다.');
    }
});

/**
 * DELETE /api/schedule/:id
 * 로그인한 사용자의 환자(user_id)에 속한 일정만 삭제합니다.
 */
router.delete('/:id', verifyToken, async (req, res) => {
    const memberId = req.user.memberId;
    const parsedScheduleId = parseNumericValue(req.params.id);

    if (parsedScheduleId === null) {
        return sendError(res, 400, '유효하지 않은 schedule id입니다.');
    }

    try {
        const userId = await findUserIdByMemberId(memberId);

        if (!userId) {
            return sendError(res, 404, '등록된 환자 정보가 없습니다.');
        }

        const deleteQuery = `
            DELETE FROM schedules
            WHERE schedule_id = $1
              AND user_id = $2
            RETURNING
                schedule_id,
                user_id,
                medication_id,
                dosage_count,
                scheduled_time,
                start_date,
                end_date,
                days_of_week,
                repeat_interval,
                status
        `;

        const { rows } = await pool.query(deleteQuery, [parsedScheduleId, userId]);

        if (rows.length === 0) {
            return sendError(res, 404, '삭제할 복약 일정이 없거나 접근 권한이 없습니다.');
        }

        return sendSuccess(res, 200, {
            message: '복약 일정이 삭제되었습니다.',
            schedule: rows[0]
        });
    } catch (error) {
        console.error('복약 일정 삭제 중 오류가 발생했습니다:', error);
        return sendError(res, 500, '복약 일정 삭제 중 서버 오류가 발생했습니다.');
    }
});

module.exports = router;
