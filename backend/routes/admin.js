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
        return res.json({
            success: true, token,
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

module.exports = router;
