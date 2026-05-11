require('dotenv').config();
const pool = require('../db');

async function seed() {
    const client = await pool.connect();
    try {
        await client.query('BEGIN');

        // ── 1. 데모 보호자 계정 ──────────────────────────────────────────────
        let { rows: memRows } = await client.query(
            "SELECT mem_id FROM members WHERE email = 'demo@carefull.app' LIMIT 1"
        );
        let memId;
        if (memRows.length === 0) {
            const r = await client.query(
                `INSERT INTO members (social_id, provider, email, nick, profile_img, joined_at)
                 VALUES ('DEMO_CAREFULL_ADMIN_VIEW', 'kakao', 'demo@carefull.app', '김보호자', '', NOW() - INTERVAL '60 days')
                 RETURNING mem_id`
            );
            memId = r.rows[0].mem_id;
            console.log(`[1] 보호자 계정 생성: mem_id=${memId}`);
        } else {
            memId = memRows[0].mem_id;
            console.log(`[1] 보호자 계정 이미 존재: mem_id=${memId}`);
        }

        // ── 2. 환자 등록 ─────────────────────────────────────────────────────
        let { rows: patRows } = await client.query(
            'SELECT patient_id FROM patients WHERE mem_id = $1 LIMIT 1', [memId]
        );
        let patientId;
        if (patRows.length === 0) {
            const r = await client.query(
                `INSERT INTO patients (mem_id, patient_name, birthdate, gender, phone, bloodtype, guardian_name, created_at)
                 VALUES ($1, '김순자', '1952-03-15', 'F', '010-1234-5678', 'A+', '김보호자', NOW() - INTERVAL '55 days')
                 RETURNING patient_id`,
                [memId]
            );
            patientId = r.rows[0].patient_id;
            console.log(`[2] 환자 등록: patient_id=${patientId}`);
        } else {
            patientId = patRows[0].patient_id;
            console.log(`[2] 환자 이미 존재: patient_id=${patientId}`);
        }

        // ── 3. 기기 등록 ─────────────────────────────────────────────────────
        const { rows: devRows } = await client.query(
            'SELECT device_id FROM devices WHERE patient_id = $1 LIMIT 1', [patientId]
        );
        if (devRows.length === 0) {
            await client.query(
                `INSERT INTO devices (device_uid, patient_id, device_status, device_name, registered_at, last_ping)
                 VALUES ('CF-DEMO-0001', $1, 'REGISTERED', '데모 디스펜서', NOW() - INTERVAL '50 days', NOW() - INTERVAL '2 hours')`,
                [patientId]
            );
            console.log('[3] 기기 등록: CF-DEMO-0001');
        } else {
            console.log('[3] 기기 이미 존재, 스킵');
        }

        // ── 4. 약 데이터 ─────────────────────────────────────────────────────
        const getMediId = async (name) => {
            let { rows } = await client.query(
                'SELECT medi_id FROM medications WHERE medi_name = $1 LIMIT 1', [name]
            );
            if (rows.length > 0) return rows[0].medi_id;
            const r = await client.query(
                'INSERT INTO medications (medi_name) VALUES ($1) RETURNING medi_id', [name]
            );
            return r.rows[0].medi_id;
        };
        const medi1 = await getMediId('아스피린 100mg (데모)');
        const medi2 = await getMediId('암로디핀 5mg (데모)');
        const medi3 = await getMediId('메트포르민 500mg (데모)');
        console.log(`[4] 약 데이터: medi_id ${medi1}, ${medi2}, ${medi3}`);

        // ── 5. 복약 스케줄 ───────────────────────────────────────────────────
        const getScheId = async (time, mediId) => {
            let { rows } = await client.query(
                "SELECT sche_id FROM schedules WHERE patient_id = $1 AND time_to_take::TEXT = $2 LIMIT 1",
                [patientId, time]
            );
            if (rows.length > 0) return rows[0].sche_id;
            const r = await client.query(
                `INSERT INTO schedules (patient_id, medi_id, time_to_take, start_date, end_date, dose_interval, status)
                 VALUES ($1, $2, $3, CURRENT_DATE - 30, CURRENT_DATE + 60, NULL, 'ACTIVE')
                 RETURNING sche_id`,
                [patientId, mediId, time]
            );
            return r.rows[0].sche_id;
        };
        const sche1 = await getScheId('08:00:00', medi1);
        const sche2 = await getScheId('13:00:00', medi2);
        const sche3 = await getScheId('20:00:00', medi3);
        console.log(`[5] 스케줄: sche_id ${sche1}, ${sche2}, ${sche3}`);

        // ── 6. 복약 로그 30일치 ──────────────────────────────────────────────
        const { rows: actCheck } = await client.query(
            'SELECT 1 FROM activities WHERE patient_id = $1 LIMIT 1', [patientId]
        );
        if (actCheck.length === 0) {
            const missedMorning = new Set([3,6,10,14,17,21,25,29]);
            const missedLunch   = new Set([2,5,9,12,16,19,23,27]);
            const missedEvening = new Set([4,9,15,21,28]);

            const makeActivity = async (scheId, dayOffset, hour, min, missedSet) => {
                const success = !missedSet.has(dayOffset);
                // KST 기준 타임스탬프 (UTC+9 오프셋 적용)
                const scheTime   = `CURRENT_DATE - ${dayOffset} + TIME '${String(hour).padStart(2,'0')}:00:00'`;
                await client.query(
                    `INSERT INTO activities
                        (sche_id, patient_id, sche_time, actual_time, status, is_face_auth, is_ai_check, similarity_score, created_at)
                     VALUES (
                         $1, $2,
                         (CURRENT_DATE - $3 + TIME '${String(hour).padStart(2,'0')}:00:00')::TIMESTAMP AT TIME ZONE 'Asia/Seoul',
                         ${success ? `(CURRENT_DATE - $3 + TIME '${String(hour).padStart(2,'0')}:0${min}:00')::TIMESTAMP AT TIME ZONE 'Asia/Seoul'` : 'NULL'},
                         $4, $5, $5,
                         ${success ? `ROUND((0.85 + ($3 % 13) * 0.008)::NUMERIC, 3)` : 'NULL'},
                         (CURRENT_DATE - $3 + TIME '${String(hour).padStart(2,'0')}:0${min + 1}:00')::TIMESTAMP AT TIME ZONE 'Asia/Seoul'
                     )`,
                    [scheId, patientId, dayOffset, success ? 'SUCCESS' : 'MISSED', success]
                );
            };

            for (let i = 1; i <= 30; i++) {
                await makeActivity(sche1, i, 8,  2, missedMorning);
                await makeActivity(sche2, i, 13, 3, missedLunch);
                await makeActivity(sche3, i, 20, 1, missedEvening);
            }
            console.log('[6] 복약 로그 90건 생성 완료');
        } else {
            console.log('[6] 복약 로그 이미 존재, 스킵');
        }

        // ── 7. 알림 10건 ─────────────────────────────────────────────────────
        const { rows: notiCheck } = await client.query(
            'SELECT 1 FROM notifications WHERE mem_id = $1 LIMIT 1', [memId]
        );
        if (notiCheck.length === 0) {
            const notis = [
                ['MISSED',  '미복용 알림', '김순자님이 오늘 점심 약을 복용하지 않으셨습니다.',         false, '1 hour'],
                ['SUCCESS', '복약 완료',   '김순자님이 오늘 아침 약을 복용하셨습니다.',                true,  '5 hours 58 minutes'],
                ['MISSED',  '미복용 알림', '김순자님이 어제 저녁 약을 복용하지 않으셨습니다.',         true,  '1 day 3 hours 30 minutes'],
                ['SUCCESS', '복약 완료',   '김순자님이 어제 점심 약을 복용하셨습니다.',                true,  '1 day 9 hours 57 minutes'],
                ['SUCCESS', '복약 완료',   '김순자님이 어제 아침 약을 복용하셨습니다.',                true,  '1 day 13 hours 57 minutes'],
                ['MISSED',  '미복용 알림', '김순자님이 이틀 전 저녁 약을 복용하지 않으셨습니다.',     true,  '2 days 3 hours 30 minutes'],
                ['SUCCESS', '복약 완료',   '김순자님이 이틀 전 점심 약을 복용하셨습니다.',             true,  '2 days 9 hours 57 minutes'],
                ['SUCCESS', '복약 완료',   '김순자님이 이틀 전 아침 약을 복용하셨습니다.',             true,  '2 days 13 hours 57 minutes'],
                ['MISSED',  '미복용 알림', '김순자님이 사흘 전 점심 약을 복용하지 않으셨습니다.',     true,  '3 days 9 hours 3 minutes'],
                ['SUCCESS', '복약 완료',   '김순자님이 사흘 전 아침 약을 복용하셨습니다.',             true,  '3 days 13 hours 58 minutes'],
            ];
            for (const [type, title, msg, received, interval] of notis) {
                await client.query(
                    `INSERT INTO notifications (mem_id, noti_type, noti_title, noti_msg, is_received, created_at)
                     VALUES ($1, $2, $3, $4, $5, NOW() - INTERVAL '${interval}')`,
                    [memId, type, title, msg, received]
                );
            }
            console.log('[7] 알림 10건 생성 완료');
        } else {
            console.log('[7] 알림 이미 존재, 스킵');
        }

        await client.query('COMMIT');
        console.log('\n✅ 데모 데이터 시드 완료!');
        console.log(`   보호자: demo@carefull.app / 환자: 김순자 / 기기: CF-DEMO-0001`);
    } catch (err) {
        await client.query('ROLLBACK');
        console.error('❌ 시드 실패 (롤백):', err.message);
        console.error(err);
    } finally {
        client.release();
        await pool.end();
    }
}

seed();
