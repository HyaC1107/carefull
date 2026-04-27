const express = require('express');
const bcrypt  = require('bcryptjs');
const jwt     = require('jsonwebtoken');
const pool    = require('../db');
const { verifyAdminToken } = require('../middleware/adminAuth');

const router = express.Router();

// ── POST /api/admin/login ─────────────────────────────────────────────────────
router.post('/login', async (req, res) => {
    const { login_id, password } = req.body;

    if (!login_id || !password) {
        return res.status(400).json({ success: false, message: '아이디와 비밀번호를 입력해주세요.' });
    }

    try {
        const { rows } = await pool.query(
            'SELECT * FROM admins WHERE login_id = $1 AND is_active = true',
            [login_id]
        );

        if (rows.length === 0) {
            return res.status(401).json({ success: false, message: '아이디 또는 비밀번호가 올바르지 않습니다.' });
        }

        const admin = rows[0];
        const match = await bcrypt.compare(password, admin.password);

        if (!match) {
            return res.status(401).json({ success: false, message: '아이디 또는 비밀번호가 올바르지 않습니다.' });
        }

        await pool.query(
            'UPDATE admins SET last_login_at = NOW() WHERE admin_id = $1',
            [admin.admin_id]
        );

        const token = jwt.sign(
            { admin_id: admin.admin_id, login_id: admin.login_id, name: admin.name, role: admin.role },
            process.env.JWT_SECRET,
            { expiresIn: '8h' }
        );

        return res.json({
            success: true,
            token,
            admin: { admin_id: admin.admin_id, login_id: admin.login_id, name: admin.name, role: admin.role },
        });
    } catch (err) {
        console.error('[ADMIN LOGIN]', err);
        return res.status(500).json({ success: false, message: '서버 오류가 발생했습니다.' });
    }
});

// ── GET /api/admin/me ─────────────────────────────────────────────────────────
router.get('/me', verifyAdminToken, (req, res) => {
    res.json({ success: true, admin: req.admin });
});

// ── GET /api/admin/stats ──────────────────────────────────────────────────────
router.get('/stats', verifyAdminToken, async (req, res) => {
    try {
        const [members, patients, todayAct, recentAct] = await Promise.all([
            pool.query('SELECT COUNT(*)::int AS cnt FROM members'),
            pool.query('SELECT COUNT(*)::int AS cnt FROM patients'),
            pool.query(`SELECT COUNT(*)::int AS cnt FROM activities
                        WHERE created_at >= CURRENT_DATE`),
            pool.query(`
                SELECT
                    a.activity_id,
                    a.created_at,
                    a.face_verified,
                    a.dispensed,
                    a.action_verified,
                    a.similarity_score,
                    p.patient_name,
                    m.nick AS member_nick
                FROM activities a
                LEFT JOIN patients p ON p.patient_id = a.patient_id
                LEFT JOIN members  m ON m.mem_id     = p.mem_id
                ORDER BY a.created_at DESC
                LIMIT 20
            `),
        ]);

        return res.json({
            success: true,
            stats: {
                total_members:    members.rows[0].cnt,
                total_patients:   patients.rows[0].cnt,
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
                m.created_at,
                COUNT(p.patient_id)::int AS patient_count
            FROM members m
            LEFT JOIN patients p ON p.mem_id = m.mem_id
            GROUP BY m.mem_id
            ORDER BY m.created_at DESC
        `);
        return res.json({ success: true, members: rows });
    } catch (err) {
        console.error('[ADMIN MEMBERS]', err);
        return res.status(500).json({ success: false, message: '서버 오류가 발생했습니다.' });
    }
});

module.exports = router;
