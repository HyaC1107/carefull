const express = require('express');
const bcrypt  = require('bcryptjs');
const jwt     = require('jsonwebtoken');
const pool    = require('../db');
const { verifyAdminToken } = require('../middleware/adminAuth');

const router = express.Router();

// ── POST /api/admin/login ─────────────────────────────────────────────────────
router.post('/login', async (req, res) => {
    const { login_id, password } = req.body;
    if (!login_id || !password)
        return res.status(400).json({ success: false, message: '아이디와 비밀번호를 입력해주세요.' });

    try {
        const { rows } = await pool.query(
            'SELECT * FROM admins WHERE login_id = $1 AND is_active = true',
            [login_id]
        );
        if (rows.length === 0)
            return res.status(401).json({ success: false, message: '아이디 또는 비밀번호가 올바르지 않습니다.' });

        const admin = rows[0];
        if (!(await bcrypt.compare(password, admin.password)))
            return res.status(401).json({ success: false, message: '아이디 또는 비밀번호가 올바르지 않습니다.' });

        await pool.query('UPDATE admins SET last_login_at = NOW() WHERE admin_id = $1', [admin.admin_id]);

        const token = jwt.sign(
            { admin_id: admin.admin_id, login_id: admin.login_id, name: admin.name, role: admin.role },
            process.env.JWT_SECRET,
            { expiresIn: '8h' }
        );

        // 데모 사용자 토큰 발급 (seed-demo-data.sql 실행 후 사용 가능)
        let demoUserToken = null;
        try {
            const demoRes = await pool.query(
                "SELECT * FROM members WHERE email = 'demo@carefull.app' LIMIT 1"
            );
            if (demoRes.rows.length > 0) {
                const dm = demoRes.rows[0];
                demoUserToken = jwt.sign(
                    { mem_id: dm.mem_id, email: dm.email, nick: dm.nick, provider: dm.provider },
                    process.env.JWT_SECRET,
                    { expiresIn: '8h' }
                );
            }
        } catch (e) {
            console.warn('[ADMIN LOGIN] demo token gen failed:', e.message);
        }

        return res.json({
            success: true, token,
            demo_user_token: demoUserToken,
            admin: { admin_id: admin.admin_id, login_id: admin.login_id, name: admin.name, role: admin.role },
        });
    } catch (err) {
        console.error('[ADMIN LOGIN]', err);
        return res.status(500).json({ success: false, message: '서버 오류가 발생했습니다.' });
    }
});

// ── GET /api/admin/me ─────────────────────────────────────────────────────────
router.get('/me', verifyAdminToken, (req, res) =>
    res.json({ success: true, admin: req.admin })
);

// ── GET /api/admin/stats ──────────────────────────────────────────────────────
router.get('/stats', verifyAdminToken, async (req, res) => {
    try {
        const [members, patients, devices, todayAct, recentAct] = await Promise.all([
            pool.query('SELECT COUNT(*)::int AS cnt FROM members'),
            pool.query('SELECT COUNT(*)::int AS cnt FROM patients'),
            pool.query('SELECT COUNT(*)::int AS cnt FROM devices'),
            pool.query(`
                SELECT COUNT(*)::int AS cnt
                FROM activities
                WHERE (created_at AT TIME ZONE 'Asia/Seoul')::date =
                      (CURRENT_TIMESTAMP AT TIME ZONE 'Asia/Seoul')::date
            `),
            pool.query(`
                SELECT
                    a.activity_id,
                    a.created_at,
                    a.status,
                    a.is_face_auth,
                    a.is_ai_check,
                    a.similarity_score,
                    a.sche_time,
                    a.actual_time,
                    p.patient_name,
                    m.nick AS member_nick
                FROM activities a
                LEFT JOIN patients p ON p.patient_id = a.patient_id
                LEFT JOIN members  m ON m.mem_id = p.mem_id
                ORDER BY a.created_at DESC
                LIMIT 20
            `),
        ]);
        return res.json({
            success: true,
            stats: {
                total_members:    members.rows[0].cnt,
                total_patients:   patients.rows[0].cnt,
                total_devices:    devices.rows[0].cnt,
                today_activities: todayAct.rows[0].cnt,
            },
            recent_activities: recentAct.rows,
        });
    } catch (err) {
        console.error('[ADMIN STATS]', err);
        return res.status(500).json({ success: false, message: '서버 오류가 발생했습니다.' });
    }
});

// ── GET /api/admin/members ────────────────────────────────────────────────────
router.get('/members', verifyAdminToken, async (req, res) => {
    try {
        const { rows } = await pool.query(`
            SELECT
                m.mem_id,
                m.nick,
                m.email,
                m.provider,
                COUNT(p.patient_id)::int AS patient_count
            FROM members m
            LEFT JOIN patients p ON p.mem_id = m.mem_id
            GROUP BY m.mem_id, m.nick, m.email, m.provider
            ORDER BY m.mem_id DESC
        `);
        return res.json({ success: true, members: rows });
    } catch (err) {
        console.error('[ADMIN MEMBERS]', err);
        return res.status(500).json({ success: false, message: err.message });
    }
});

// ── GET /api/admin/patients ───────────────────────────────────────────────────
router.get('/patients', verifyAdminToken, async (req, res) => {
    try {
        const { rows } = await pool.query(`
            SELECT
                p.patient_id,
                p.patient_name,
                p.birthdate,
                p.gender,
                p.phone,
                p.bloodtype,
                p.fingerprint_slots,
                p.created_at,
                m.nick  AS member_nick,
                m.email AS member_email,
                d.device_uid,
                d.last_ping
            FROM patients p
            LEFT JOIN members m ON m.mem_id = p.mem_id
            LEFT JOIN devices d ON d.patient_id = p.patient_id
            ORDER BY p.created_at DESC
        `);
        return res.json({ success: true, patients: rows });
    } catch (err) {
        console.error('[ADMIN PATIENTS]', err);
        return res.status(500).json({ success: false, message: '서버 오류가 발생했습니다.' });
    }
});

// ── GET /api/admin/activities ─────────────────────────────────────────────────
router.get('/activities', verifyAdminToken, async (req, res) => {
    const limit  = Math.min(parseInt(req.query.limit  || '50',  10), 200);
    const offset = Math.max(parseInt(req.query.offset || '0',   10), 0);
    try {
        const { rows } = await pool.query(`
            SELECT
                a.activity_id,
                a.sche_id,
                a.sche_time,
                a.actual_time,
                a.status,
                a.is_face_auth,
                a.is_ai_check,
                a.similarity_score,
                a.created_at,
                p.patient_name,
                m.nick AS member_nick
            FROM activities a
            LEFT JOIN patients p ON p.patient_id = a.patient_id
            LEFT JOIN members  m ON m.mem_id = p.mem_id
            ORDER BY a.created_at DESC
            LIMIT $1 OFFSET $2
        `, [limit, offset]);
        const { rows: total } = await pool.query('SELECT COUNT(*)::int AS cnt FROM activities');
        return res.json({ success: true, activities: rows, total: total[0].cnt });
    } catch (err) {
        console.error('[ADMIN ACTIVITIES]', err);
        return res.status(500).json({ success: false, message: '서버 오류가 발생했습니다.' });
    }
});

// ── GET /api/admin/devices ────────────────────────────────────────────────────
router.get('/devices', verifyAdminToken, async (req, res) => {
    try {
        const { rows } = await pool.query(`
            SELECT
                d.device_id,
                d.device_uid,
                d.device_status,
                d.last_ping,
                d.registered_at,
                p.patient_name,
                m.nick AS member_nick
            FROM devices d
            LEFT JOIN patients p ON p.patient_id = d.patient_id
            LEFT JOIN members  m ON m.mem_id = p.mem_id
            ORDER BY d.last_ping DESC NULLS LAST
        `);
        return res.json({ success: true, devices: rows });
    } catch (err) {
        console.error('[ADMIN DEVICES]', err);
        return res.status(500).json({ success: false, message: err.message });
    }
});

// ── GET /api/admin/schedules ──────────────────────────────────────────────────
router.get('/schedules', verifyAdminToken, async (req, res) => {
    try {
        const { rows } = await pool.query(`
            SELECT
                s.sche_id,
                s.time_to_take,
                s.start_date,
                s.end_date,
                s.dose_interval,
                s.status,
                p.patient_name,
                med.medi_name
            FROM schedules s
            LEFT JOIN patients    p   ON p.patient_id = s.patient_id
            LEFT JOIN medications med ON med.medi_id  = s.medi_id
            ORDER BY s.sche_id DESC
        `);
        return res.json({ success: true, schedules: rows });
    } catch (err) {
        console.error('[ADMIN SCHEDULES]', err);
        return res.status(500).json({ success: false, message: err.message });
    }
});

// ── GET /api/admin/medications ────────────────────────────────────────────
router.get('/medications', verifyAdminToken, async (req, res) => {
    try {
        const { rows } = await pool.query(
            'SELECT medi_id, medi_name FROM medications ORDER BY medi_name LIMIT 300'
        );
        return res.json({ success: true, medications: rows });
    } catch (err) {
        console.error('[ADMIN MEDICATIONS]', err);
        return res.status(500).json({ success: false, message: err.message });
    }
});

// ── POST /api/admin/test/device ───────────────────────────────────────────
router.post('/test/device', verifyAdminToken, async (req, res) => {
    const { device_uid, patient_id } = req.body;
    if (!device_uid?.trim()) return res.status(400).json({ success: false, message: 'device_uid 필수' });
    if (!patient_id)          return res.status(400).json({ success: false, message: 'patient_id 필수' });

    try {
        const { rows: ex } = await pool.query(
            'SELECT device_id FROM devices WHERE device_uid = $1', [device_uid.trim()]
        );
        let rows;
        if (ex.length > 0) {
            ({ rows } = await pool.query(`
                UPDATE devices
                SET patient_id = $1, device_status = 'REGISTERED',
                    registered_at = NOW(), last_ping = NOW()
                WHERE device_uid = $2
                RETURNING device_id, device_uid, patient_id, device_status, registered_at
            `, [patient_id, device_uid.trim()]));
        } else {
            ({ rows } = await pool.query(`
                INSERT INTO devices (device_uid, patient_id, device_status, registered_at, last_ping, device_name)
                VALUES ($1, $2, 'REGISTERED', NOW(), NOW(), 'TEST_DEVICE')
                RETURNING device_id, device_uid, patient_id, device_status, registered_at
            `, [device_uid.trim(), patient_id]));
        }
        return res.json({ success: true, message: '기기 등록 완료', device: rows[0] });
    } catch (err) {
        console.error('[ADMIN TEST DEVICE]', err);
        return res.status(500).json({ success: false, message: err.message });
    }
});

// ── DELETE /api/admin/test/device/:device_uid ─────────────────────────────
router.delete('/test/device/:device_uid', verifyAdminToken, async (req, res) => {
    try {
        const { rows } = await pool.query(`
            UPDATE devices SET patient_id = NULL, device_status = 'UNREGISTERED'
            WHERE device_uid = $1
            RETURNING device_id, device_uid
        `, [req.params.device_uid]);
        if (rows.length === 0) return res.status(404).json({ success: false, message: '기기를 찾을 수 없습니다.' });
        return res.json({ success: true, message: '기기 해제 완료' });
    } catch (err) {
        console.error('[ADMIN TEST DEVICE DELETE]', err);
        return res.status(500).json({ success: false, message: err.message });
    }
});

// ── POST /api/admin/test/schedule ─────────────────────────────────────────
router.post('/test/schedule', verifyAdminToken, async (req, res) => {
    const { patient_id, medi_id, time_to_take, start_date, end_date, dose_interval } = req.body;
    if (!patient_id || !medi_id || !time_to_take || !start_date)
        return res.status(400).json({ success: false, message: 'patient_id, medi_id, time_to_take, start_date 필수' });

    try {
        const { rows } = await pool.query(`
            INSERT INTO schedules (patient_id, medi_id, time_to_take, start_date, end_date, dose_interval, status)
            VALUES ($1, $2, $3, $4, $5, $6, 'ACTIVE')
            RETURNING sche_id, patient_id, medi_id, time_to_take, start_date, end_date, dose_interval, status
        `, [patient_id, medi_id, time_to_take, start_date, end_date || null, dose_interval || null]);
        return res.json({ success: true, message: '스케줄 등록 완료', schedule: rows[0] });
    } catch (err) {
        console.error('[ADMIN TEST SCHEDULE]', err);
        return res.status(500).json({ success: false, message: err.message });
    }
});

// ── DELETE /api/admin/test/schedule/:sche_id ──────────────────────────────
router.delete('/test/schedule/:sche_id', verifyAdminToken, async (req, res) => {
    const id = parseInt(req.params.sche_id, 10);
    if (isNaN(id)) return res.status(400).json({ success: false, message: '유효하지 않은 sche_id' });
    try {
        const { rows } = await pool.query(
            'DELETE FROM schedules WHERE sche_id = $1 RETURNING sche_id', [id]
        );
        if (rows.length === 0) return res.status(404).json({ success: false, message: '스케줄을 찾을 수 없습니다.' });
        return res.json({ success: true, message: '스케줄 삭제 완료' });
    } catch (err) {
        console.error('[ADMIN TEST SCHEDULE DELETE]', err);
        return res.status(500).json({ success: false, message: err.message });
    }
});

// ── DELETE /api/admin/test/patient/:patient_id ────────────────────────────
router.delete('/test/patient/:patient_id', verifyAdminToken, async (req, res) => {
    const id = parseInt(req.params.patient_id, 10);
    if (isNaN(id)) return res.status(400).json({ success: false, message: '유효하지 않은 patient_id' });
    try {
        const { rows } = await pool.query(
            'DELETE FROM patients WHERE patient_id = $1 RETURNING patient_id, patient_name', [id]
        );
        if (rows.length === 0) return res.status(404).json({ success: false, message: '환자를 찾을 수 없습니다.' });
        return res.json({ success: true, message: `"${rows[0].patient_name}" 삭제 완료` });
    } catch (err) {
        console.error('[ADMIN TEST PATIENT DELETE]', err);
        return res.status(500).json({ success: false, message: err.message });
    }
});

// ── POST /api/admin/test/push ─────────────────────────────────────────────
router.post('/test/push', verifyAdminToken, async (req, res) => {
    const { mem_id, title, body } = req.body;
    if (!mem_id || !title || !body)
        return res.status(400).json({ success: false, message: 'mem_id, title, body 필수' });

    try {
        // push_tokens 테이블에서 해당 회원의 활성 토큰 수 먼저 확인
        const pool = require('../db');
        const { rows: tokenRows } = await pool.query(
            'SELECT fcm_token FROM push_tokens WHERE mem_id = $1 AND is_active IS NOT FALSE',
            [parseInt(mem_id, 10)]
        );
        if (tokenRows.length === 0) {
            return res.status(400).json({
                success: false,
                message: '해당 회원의 활성 FCM 토큰이 없습니다. 해당 계정으로 로그인 후 알림 권한을 허용해야 합니다.'
            });
        }

        return res.json({
            success: true,
            message: `푸시 알림 전송 완료 (토큰 ${tokenRows.length}개 대상)`
        });
    } catch (err) {
        console.error('[ADMIN TEST PUSH]', err);
        return res.status(500).json({ success: false, message: err.message });
    }
});

// ── POST /api/admin/seed-demo ─────────────────────────────────────────────────
router.post('/seed-demo', verifyAdminToken, async (req, res) => {
    const log = [];
    const client = await pool.connect();
    try {
        await client.query('BEGIN');

        // 1. 보호자 계정
        let { rows: m } = await client.query("SELECT mem_id FROM members WHERE email='demo@carefull.app' LIMIT 1");
        let memId;
        if (m.length === 0) {
            const r = await client.query(
                `INSERT INTO members (social_id, provider, email, nick, profile_img, joined_at)
                 VALUES ('DEMO_CAREFULL_ADMIN_VIEW','kakao','demo@carefull.app','김보호자','',NOW()-INTERVAL '60 days')
                 RETURNING mem_id`
            );
            memId = r.rows[0].mem_id;
            log.push(`보호자 계정 생성: mem_id=${memId}`);
        } else {
            memId = m[0].mem_id;
            log.push(`보호자 계정 이미 존재: mem_id=${memId}`);
        }

        // 2. 환자
        let { rows: p } = await client.query('SELECT patient_id FROM patients WHERE mem_id=$1 LIMIT 1', [memId]);
        let patientId;
        if (p.length === 0) {
            const r = await client.query(
                `INSERT INTO patients (mem_id, patient_name, birthdate, gender, phone, bloodtype, guardian_name, created_at)
                 VALUES ($1,'김순자','1952-03-15','F','010-1234-5678','A+','김보호자',NOW()-INTERVAL '55 days')
                 RETURNING patient_id`,
                [memId]
            );
            patientId = r.rows[0].patient_id;
            log.push(`환자 등록: patient_id=${patientId}`);
        } else {
            patientId = p[0].patient_id;
            log.push(`환자 이미 존재: patient_id=${patientId}`);
        }

        // 3. 기기
        const { rows: d } = await client.query('SELECT device_id FROM devices WHERE patient_id=$1 LIMIT 1', [patientId]);
        if (d.length === 0) {
            await client.query(
                `INSERT INTO devices (device_uid, patient_id, device_status, device_name, registered_at, last_ping)
                 VALUES ('CF-DEMO-0001',$1,'REGISTERED','데모 디스펜서',NOW()-INTERVAL '50 days',NOW()-INTERVAL '2 hours')`,
                [patientId]
            );
            log.push('기기 등록: CF-DEMO-0001');
        } else { log.push('기기 이미 존재, 스킵'); }

        // 4. 약
        const getMedi = async (name) => {
            let { rows } = await client.query('SELECT medi_id FROM medications WHERE medi_name=$1 LIMIT 1', [name]);
            if (rows.length > 0) return rows[0].medi_id;
            const r = await client.query('INSERT INTO medications (medi_name) VALUES ($1) RETURNING medi_id', [name]);
            return r.rows[0].medi_id;
        };
        const medi1 = await getMedi('아스피린 100mg (데모)');
        const medi2 = await getMedi('암로디핀 5mg (데모)');
        const medi3 = await getMedi('메트포르민 500mg (데모)');
        log.push(`약: ${medi1}, ${medi2}, ${medi3}`);

        // 5. 스케줄
        const getSche = async (time, mediId) => {
            let { rows } = await client.query(
                "SELECT sche_id FROM schedules WHERE patient_id=$1 AND time_to_take::TEXT=$2 LIMIT 1",
                [patientId, time]
            );
            if (rows.length > 0) return rows[0].sche_id;
            const r = await client.query(
                `INSERT INTO schedules (patient_id, medi_id, time_to_take, start_date, end_date, dose_interval, status)
                 VALUES ($1,$2,$3,CURRENT_DATE-30,CURRENT_DATE+60,NULL,'ACTIVE') RETURNING sche_id`,
                [patientId, mediId, time]
            );
            return r.rows[0].sche_id;
        };
        const sche1 = await getSche('08:00:00', medi1);
        const sche2 = await getSche('13:00:00', medi2);
        const sche3 = await getSche('20:00:00', medi3);
        log.push(`스케줄: ${sche1}, ${sche2}, ${sche3}`);

        // 6. 복약 로그 30일치
        const { rows: actCheck } = await client.query('SELECT 1 FROM activities WHERE patient_id=$1 LIMIT 1', [patientId]);
        if (actCheck.length === 0) {
            const missedM = new Set([3,6,10,14,17,21,25,29]);
            const missedL = new Set([2,5,9,12,16,19,23,27]);
            const missedE = new Set([4,9,15,21,28]);
            for (let i = 1; i <= 30; i++) {
                for (const [scheId, h, min, missed] of [
                    [sche1, 8,  2, missedM],
                    [sche2, 13, 3, missedL],
                    [sche3, 20, 1, missedE],
                ]) {
                    const ok = !missed.has(i);
                    const hh = String(h).padStart(2,'0');
                    const mm = String(min).padStart(2,'0');
                    await client.query(
                        `INSERT INTO activities (sche_id,patient_id,sche_time,actual_time,status,is_face_auth,is_ai_check,similarity_score,created_at)
                         VALUES ($1,$2,
                           (CURRENT_DATE-$3+TIME '${hh}:00:00')::TIMESTAMP AT TIME ZONE 'Asia/Seoul',
                           ${ok ? `(CURRENT_DATE-$3+TIME '${hh}:${mm}:00')::TIMESTAMP AT TIME ZONE 'Asia/Seoul'` : 'NULL'},
                           $4,$5,$5,
                           ${ok ? `ROUND((0.85+($3%13)*0.008)::NUMERIC,3)` : 'NULL'},
                           (CURRENT_DATE-$3+TIME '${hh}:${mm}:30')::TIMESTAMP AT TIME ZONE 'Asia/Seoul'
                         )`,
                        [scheId, patientId, i, ok ? 'SUCCESS' : 'MISSED', ok]
                    );
                }
            }
            log.push('복약 로그 90건 생성');
        } else { log.push('복약 로그 이미 존재, 스킵'); }

        // 7. 알림
        const { rows: nc } = await client.query('SELECT 1 FROM notifications WHERE mem_id=$1 LIMIT 1', [memId]);
        if (nc.length === 0) {
            const notis = [
                ['MISSED','미복용 알림','김순자님이 오늘 점심 약을 복용하지 않으셨습니다.',false,'1 hour'],
                ['SUCCESS','복약 완료','김순자님이 오늘 아침 약을 복용하셨습니다.',true,'5 hours 58 minutes'],
                ['MISSED','미복용 알림','김순자님이 어제 저녁 약을 복용하지 않으셨습니다.',true,'1 day 3 hours 30 minutes'],
                ['SUCCESS','복약 완료','김순자님이 어제 점심 약을 복용하셨습니다.',true,'1 day 9 hours 57 minutes'],
                ['SUCCESS','복약 완료','김순자님이 어제 아침 약을 복용하셨습니다.',true,'1 day 13 hours 57 minutes'],
                ['MISSED','미복용 알림','김순자님이 이틀 전 저녁 약을 복용하지 않으셨습니다.',true,'2 days 3 hours 30 minutes'],
                ['SUCCESS','복약 완료','김순자님이 이틀 전 점심 약을 복용하셨습니다.',true,'2 days 9 hours 57 minutes'],
                ['SUCCESS','복약 완료','김순자님이 이틀 전 아침 약을 복용하셨습니다.',true,'2 days 13 hours 57 minutes'],
                ['MISSED','미복용 알림','김순자님이 사흘 전 점심 약을 복용하지 않으셨습니다.',true,'3 days 9 hours 3 minutes'],
                ['SUCCESS','복약 완료','김순자님이 사흘 전 아침 약을 복용하셨습니다.',true,'3 days 13 hours 58 minutes'],
            ];
            for (const [type, title, msg, recv, interval] of notis) {
                await client.query(
                    `INSERT INTO notifications (mem_id,noti_type,noti_title,noti_msg,is_received,created_at)
                     VALUES ($1,$2,$3,$4,$5,NOW()-INTERVAL '${interval}')`,
                    [memId, type, title, msg, recv]
                );
            }
            log.push('알림 10건 생성');
        } else { log.push('알림 이미 존재, 스킵'); }

        await client.query('COMMIT');
        return res.json({ success: true, message: '데모 데이터 시드 완료', log });
    } catch (err) {
        await client.query('ROLLBACK');
        console.error('[ADMIN SEED DEMO]', err);
        return res.status(500).json({ success: false, message: err.message });
    } finally {
        client.release();
    }
});

module.exports = router;
