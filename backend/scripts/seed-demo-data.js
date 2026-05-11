require('dotenv').config();
const pool = require('../db');

const DEMO_MEMBER_EMAIL = 'demo@carefull.app';
const DEMO_PATIENT_NAME = '김순자';
const DEMO_DEVICE_UID = 'CF-DEMO-0001';
const DEMO_START_DATE = '2026-03-01';
const DEMO_END_DATE = '2026-05-31';

async function seed() {
    const client = await pool.connect();

    try {
        await client.query('BEGIN');

        const memId = await upsertDemoMember(client);
        const patientId = await upsertDemoPatient(client, memId);
        await upsertDemoDevice(client, patientId);

        const medi1 = await getMediId(client, '아스피린 100mg (데모)');
        const medi2 = await getMediId(client, '암로디핀 5mg (데모)');
        const medi3 = await getMediId(client, '메트포르민 500mg (데모)');
        const medi4 = await getMediId(client, '오메가3 1000mg (데모)');
        const medi5 = await getMediId(client, '비타민D 1000IU (데모)');
        console.log(`[4] 약 데이터: medi_id ${medi1}, ${medi2}, ${medi3}, ${medi4}, ${medi5}`);

        const sche1 = await upsertSchedule(client, patientId, medi1, '08:00:00');
        const sche2 = await upsertSchedule(client, patientId, medi2, '10:30:00');
        const sche3 = await upsertSchedule(client, patientId, medi3, '13:00:00');
        const sche4 = await upsertSchedule(client, patientId, medi4, '16:30:00');
        const sche5 = await upsertSchedule(client, patientId, medi5, '20:00:00');
        console.log(`[5] 스케줄: sche_id ${sche1}, ${sche2}, ${sche3}, ${sche4}, ${sche5}`);

        await resetDemoLogs(client, memId, patientId);

        const dayCount = daysBetween(DEMO_START_DATE, DEMO_END_DATE);
        for (let dayIndex = 0; dayIndex < dayCount; dayIndex++) {
            const date = addDays(DEMO_START_DATE, dayIndex);

            await insertActivity(client, patientId, buildDemoActivity({
                scheId: sche1,
                date,
                time: '08:00:00',
                dayIndex,
                missed: dayIndex % 9 === 2 || dayIndex % 17 === 8,
                baseDelayMinutes: 2,
            }));
            await insertActivity(client, patientId, buildDemoActivity({
                scheId: sche2,
                date,
                time: '10:30:00',
                dayIndex,
                missed: dayIndex % 13 === 6,
                baseDelayMinutes: 3,
            }));
            await insertActivity(client, patientId, buildDemoActivity({
                scheId: sche3,
                date,
                time: '13:00:00',
                dayIndex,
                missed: dayIndex % 7 === 4 || dayIndex % 19 === 10,
                baseDelayMinutes: 4,
            }));
            await insertActivity(client, patientId, buildDemoActivity({
                scheId: sche4,
                date,
                time: '16:30:00',
                dayIndex,
                missed: dayIndex % 10 === 3 || dayIndex % 23 === 12,
                baseDelayMinutes: 5,
            }));
            await insertActivity(client, patientId, buildDemoActivity({
                scheId: sche5,
                date,
                time: '20:00:00',
                dayIndex,
                missed: dayIndex % 11 === 5,
                baseDelayMinutes: 3,
            }));
        }
        console.log(`[6] 복약 로그 ${dayCount * 5}건 생성 완료 (${DEMO_START_DATE} ~ ${DEMO_END_DATE})`);

        const notificationCount = await insertDemoNotifications(client, memId, patientId);
        console.log(`[7] 알림 ${notificationCount}건 생성 완료`);

        await client.query('COMMIT');
        console.log('\n✅ 데모 데이터 시드 완료!');
        console.log(`   보호자: ${DEMO_MEMBER_EMAIL} / 환자: ${DEMO_PATIENT_NAME} / 기기: ${DEMO_DEVICE_UID}`);
    } catch (err) {
        await client.query('ROLLBACK');
        console.error('❌ 시드 실패 (롤백):', err.message);
        console.error(err);
    } finally {
        client.release();
        await pool.end();
    }
}

async function upsertDemoMember(client) {
    const { rows } = await client.query(
        'SELECT mem_id FROM members WHERE email = $1 LIMIT 1',
        [DEMO_MEMBER_EMAIL]
    );

    if (rows.length > 0) {
        console.log(`[1] 보호자 계정 이미 존재: mem_id=${rows[0].mem_id}`);
        return rows[0].mem_id;
    }

    const inserted = await client.query(
        `INSERT INTO members (social_id, provider, email, nick, profile_img, joined_at)
         VALUES ('DEMO_CAREFULL_ADMIN_VIEW', 'kakao', $1, '김보호자', '', $2::date)
         RETURNING mem_id`,
        [DEMO_MEMBER_EMAIL, DEMO_START_DATE]
    );
    console.log(`[1] 보호자 계정 생성: mem_id=${inserted.rows[0].mem_id}`);
    return inserted.rows[0].mem_id;
}

async function upsertDemoPatient(client, memId) {
    const { rows } = await client.query(
        'SELECT patient_id FROM patients WHERE mem_id = $1 LIMIT 1',
        [memId]
    );

    if (rows.length > 0) {
        console.log(`[2] 환자 이미 존재: patient_id=${rows[0].patient_id}`);
        return rows[0].patient_id;
    }

    const inserted = await client.query(
        `INSERT INTO patients (mem_id, patient_name, birthdate, gender, phone, bloodtype, guardian_name, created_at)
         VALUES ($1, $2, '1952-03-15', 'F', '010-1234-5678', 'A+', '김보호자', $3::date)
         RETURNING patient_id`,
        [memId, DEMO_PATIENT_NAME, DEMO_START_DATE]
    );
    console.log(`[2] 환자 등록: patient_id=${inserted.rows[0].patient_id}`);
    return inserted.rows[0].patient_id;
}

async function upsertDemoDevice(client, patientId) {
    const { rows } = await client.query(
        'SELECT device_id FROM devices WHERE device_uid = $1 LIMIT 1',
        [DEMO_DEVICE_UID]
    );

    if (rows.length > 0) {
        await client.query(
            `UPDATE devices
             SET patient_id = $1,
                 device_status = 'REGISTERED',
                 device_name = '데모 디스펜서',
                 last_ping = NOW() - INTERVAL '10 minutes'
             WHERE device_uid = $2`,
            [patientId, DEMO_DEVICE_UID]
        );
        console.log('[3] 기기 이미 존재, 최신 상태로 갱신');
        return;
    }

    await client.query(
        `INSERT INTO devices (device_uid, patient_id, device_status, device_name, registered_at, last_ping)
         VALUES ($1, $2, 'REGISTERED', '데모 디스펜서', $3::date, NOW() - INTERVAL '10 minutes')`,
        [DEMO_DEVICE_UID, patientId, DEMO_START_DATE]
    );
    console.log(`[3] 기기 등록: ${DEMO_DEVICE_UID}`);
}

async function getMediId(client, name) {
    const { rows } = await client.query(
        'SELECT medi_id FROM medications WHERE medi_name = $1 LIMIT 1',
        [name]
    );
    if (rows.length > 0) return rows[0].medi_id;

    const inserted = await client.query(
        'INSERT INTO medications (medi_name) VALUES ($1) RETURNING medi_id',
        [name]
    );
    return inserted.rows[0].medi_id;
}

async function upsertSchedule(client, patientId, mediId, time) {
    const { rows } = await client.query(
        'SELECT sche_id FROM schedules WHERE patient_id = $1 AND time_to_take::text = $2 LIMIT 1',
        [patientId, time]
    );

    if (rows.length > 0) {
        await client.query(
            `UPDATE schedules
             SET medi_id = $1,
                 start_date = $2::date,
                 end_date = $3::date,
                 dose_interval = 1,
                 status = 'ACTIVE',
                 created_at = $2::date
             WHERE sche_id = $4`,
            [mediId, DEMO_START_DATE, DEMO_END_DATE, rows[0].sche_id]
        );
        return rows[0].sche_id;
    }

    const inserted = await client.query(
        `INSERT INTO schedules (patient_id, medi_id, time_to_take, start_date, end_date, dose_interval, status, created_at)
         VALUES ($1, $2, $3, $4::date, $5::date, 1, 'ACTIVE', $4::date)
         RETURNING sche_id`,
        [patientId, mediId, time, DEMO_START_DATE, DEMO_END_DATE]
    );
    return inserted.rows[0].sche_id;
}

async function resetDemoLogs(client, memId, patientId) {
    await client.query(
        'DELETE FROM notifications WHERE mem_id = $1 AND patient_id = $2',
        [memId, patientId]
    );
    await client.query('DELETE FROM activities WHERE patient_id = $1', [patientId]);
}

function buildDemoActivity({ scheId, date, time, dayIndex, missed, baseDelayMinutes }) {
    const success = !missed;
    const delayMinutes = baseDelayMinutes + (dayIndex % 4);
    const createdDelayMinutes = success ? delayMinutes + 1 : 31;

    return {
        scheId,
        date,
        time,
        actualTime: addMinutesToTime(time, delayMinutes),
        createdTime: addMinutesToTime(time, createdDelayMinutes),
        status: success ? 'SUCCESS' : 'MISSED',
        success,
        score: (0.86 + (dayIndex % 12) * 0.009).toFixed(3),
    };
}

async function insertActivity(client, patientId, activity) {
    await client.query(
        `INSERT INTO activities
            (sche_id, patient_id, sche_time, actual_time, status, is_face_auth, is_ai_check, similarity_score, created_at)
         VALUES (
             $1,
             $2,
             ($3::date + $4::time)::timestamp AT TIME ZONE 'Asia/Seoul',
             CASE WHEN $7::boolean THEN ($3::date + $5::time)::timestamp AT TIME ZONE 'Asia/Seoul' ELSE NULL END,
             $6,
             $7,
             $7,
             CASE WHEN $7::boolean THEN $8::numeric ELSE NULL END,
             ($3::date + $9::time)::timestamp AT TIME ZONE 'Asia/Seoul'
         )`,
        [
            activity.scheId,
            patientId,
            activity.date,
            activity.time,
            activity.actualTime,
            activity.status,
            activity.success,
            activity.score,
            activity.createdTime,
        ]
    );
}

async function insertDemoNotifications(client, memId, patientId) {
    const { rows: missedRows } = await client.query(
        `SELECT activity_id, sche_time
         FROM activities
         WHERE patient_id = $1 AND status = 'MISSED'
         ORDER BY sche_time DESC
         LIMIT 12`,
        [patientId]
    );
    const { rows: successRows } = await client.query(
        `SELECT activity_id, sche_time
         FROM activities
         WHERE patient_id = $1 AND status = 'SUCCESS'
         ORDER BY sche_time DESC
         LIMIT 12`,
        [patientId]
    );

    const notifications = [];

    missedRows.forEach((row, index) => {
        notifications.push({
            activityId: row.activity_id,
            type: 'MISSED',
            title: '미복용 알림',
            message: `${DEMO_PATIENT_NAME}님이 예정된 약을 복용하지 않으셨습니다.`,
            isRead: index > 3,
            createdAt: row.sche_time,
        });
    });

    successRows.forEach((row, index) => {
        notifications.push({
            activityId: row.activity_id,
            type: 'SUCCESS',
            title: '복약 완료',
            message: `${DEMO_PATIENT_NAME}님이 복약을 정상적으로 완료했습니다.`,
            isRead: index > 5,
            createdAt: row.sche_time,
        });
    });

    notifications.push(
        {
            type: 'LOW_STOCK',
            title: '약 재고 주의',
            message: '아스피린 100mg 남은 복약 가능 횟수가 부족합니다.',
            isRead: false,
            createdAt: '2026-05-11 09:20:00+09',
        },
        {
            type: 'ERROR',
            title: '기기 연결 주의',
            message: '복약 디스펜서 동기화가 일시적으로 지연되었습니다.',
            isRead: false,
            createdAt: '2026-05-10 18:15:00+09',
        },
        {
            type: 'LOW_STOCK',
            title: '약 재고 주의',
            message: '메트포르민 500mg 재고를 확인해주세요.',
            isRead: true,
            createdAt: '2026-05-09 12:10:00+09',
        },
        {
            type: 'FAILED',
            title: '복약 확인 주의',
            message: '복약 동작 인식이 불안정했습니다. 보호자 확인이 필요합니다.',
            isRead: true,
            createdAt: '2026-05-08 20:35:00+09',
        },
        {
            type: 'ERROR',
            title: '카메라 점검 필요',
            message: '카메라 인식 품질이 낮아 기기 위치 확인이 필요합니다.',
            isRead: true,
            createdAt: '2026-05-07 08:40:00+09',
        },
        {
            type: 'LOW_STOCK',
            title: '약 재고 주의',
            message: '비타민D 1000IU 재고가 일주일 이내 소진될 수 있습니다.',
            isRead: true,
            createdAt: '2026-05-06 16:20:00+09',
        }
    );

    notifications.sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt));

    for (const notification of notifications) {
        await client.query(
            `INSERT INTO notifications
                (mem_id, patient_id, activity_id, noti_type, noti_title, noti_msg, is_received, created_at)
             VALUES ($1, $2, $3, $4, $5, $6, $7, $8)`,
            [
                memId,
                patientId,
                notification.activityId || null,
                notification.type,
                notification.title,
                notification.message,
                notification.isRead,
                notification.createdAt,
            ]
        );
    }

    return notifications.length;
}
function daysBetween(startDate, endDate) {
    const start = new Date(`${startDate}T00:00:00Z`);
    const end = new Date(`${endDate}T00:00:00Z`);
    return Math.floor((end - start) / 86400000) + 1;
}

function addDays(startDate, offset) {
    const date = new Date(`${startDate}T00:00:00Z`);
    date.setUTCDate(date.getUTCDate() + offset);
    return date.toISOString().slice(0, 10);
}

function addMinutesToTime(time, minutesToAdd) {
    const [hour, minute, second] = time.split(':').map(Number);
    const date = new Date(Date.UTC(2000, 0, 1, hour, minute, second));
    date.setUTCMinutes(date.getUTCMinutes() + minutesToAdd);
    return date.toISOString().slice(11, 19);
}

seed();
