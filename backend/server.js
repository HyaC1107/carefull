require('dotenv').config();

const express = require('express');
const http = require('http');
const cors = require('cors');
const path = require('path');

const pool = require('./db');

const user_router = require('./routes/user');
const patient_router = require('./routes/patient');
const medication_router = require('./routes/medication');
const schedule_router = require('./routes/schedule');
const dashboard_router = require('./routes/dashboard');
const device_router = require('./routes/device');
const face_data_router = require('./routes/face-data');
const notification_router = require('./routes/notification');
const activity_router = require('./routes/activity');

const { startMissedLogJob } = require('./jobs/missed-activity-job');

const app = express();

// ─────────────────────────── CORS ────────────────────────────────────────────
// .env 에 ALLOWED_ORIGINS=https://carefull.vercel.app 형태로 입력
// 여러 개면 콤마 구분: https://aaa.com,https://bbb.com
const allowed_origins = (process.env.ALLOWED_ORIGINS || '')
    .split(',')
    .map(o => o.trim())
    .filter(Boolean);

app.use(cors({
    origin: (origin, callback) => {
        // 서버→서버 호출(origin 없음) 또는 허용 목록 통과
        if (!origin || allowed_origins.includes(origin)) return callback(null, true);
        callback(new Error(`CORS blocked: ${origin}`));
    },
    credentials: true,
    methods: ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS'],
    allowedHeaders: ['Content-Type', 'Authorization'],
}));

app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true, limit: '10mb' }));
app.use(express.static(path.join(__dirname, 'public')));
app.use('/uploads', express.static(path.join(__dirname, 'uploads')));

// ─────────────────────────── Health Check ────────────────────────────────────
app.get('/health', async (req, res) => {
    try {
        await pool.query('SELECT 1');
        return res.status(200).json({ status: 'ok', db: 'connected' });
    } catch {
        return res.status(503).json({ status: 'error', db: 'disconnected' });
    }
});

// ─────────────────────────── Routes ──────────────────────────────────────────
app.use('/api/user',         user_router);
app.use('/api/patient',      patient_router);
app.use('/api/medication',   medication_router);
app.use('/api/schedule',     schedule_router);
app.use('/api/dashboard',    dashboard_router);
app.use('/api/device',       device_router);
app.use('/api/face-data',    face_data_router);
app.use('/api/notification', notification_router);
app.use('/api/log',          activity_router);

// ─────────────────────────── Server ──────────────────────────────────────────
// SSL 종료는 nginx 또는 ALB 에서 처리 → Node.js 는 HTTP 로만 실행
const PORT = process.env.PORT || 3000;
const server = http.createServer(app);

server.listen(PORT, () => {
    console.log(`✅ Care-full server running on port ${PORT}`);
    startMissedLogJob();
});

// ─────────────────────────── Graceful Shutdown ───────────────────────────────
const graceful_shutdown = async (signal) => {
    console.log(`\n[${signal}] Shutting down gracefully...`);
    server.close(async () => {
        await pool.end();
        console.log('DB pool closed.');
        process.exit(0);
    });
    setTimeout(() => {
        console.error('Forced shutdown after timeout.');
        process.exit(1);
    }, 10_000);
};

process.on('SIGTERM', () => graceful_shutdown('SIGTERM')); // AWS / PM2 종료 신호
process.on('SIGINT',  () => graceful_shutdown('SIGINT'));  // Ctrl+C
