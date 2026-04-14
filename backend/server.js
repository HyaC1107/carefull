require('dotenv').config();

const express = require('express');
const https = require('https');
const fs = require('fs');
const cors = require('cors');
const path = require('path');
const pool = require('./db');

const userRouter = require('./routes/user');
const patientRouter = require('./routes/patient');
const medicationRouter = require('./routes/medication');
const scheduleRouter = require('./routes/schedule');
const dashboardRouter = require('./routes/dashboard');
const deviceRouter = require('./routes/device');
const faceDataRouter = require('./routes/face-data');
const notificationRouter = require('./routes/notification');
const logRouter = require('./routes/log');

const { startMissedLogJob } = require('./jobs/missed-log-job');
startMissedLogJob();

const app = express();
const PORT = 443;

// 공통 미들웨어
app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// 정적 파일 제공
app.use(express.static(path.join(__dirname, 'public')));
app.use('/uploads', express.static(path.join(__dirname, 'uploads')));

// HTTPS 인증서 설정
const sslOptions = {
    key: fs.readFileSync('localhost+2-key.pem'),
    cert: fs.readFileSync('localhost+2.pem')
};

/**
 * 라우터 마운트
 *
 * 왜 수정했는가:
 * - patient.js가 존재해도 서버에 마운트되지 않으면 /api/patient/* 경로는 동작하지 않습니다.
 * - 로그인 -> 환자등록 -> 조회 흐름을 patient 라우터 기준으로 연결하려면 반드시 마운트가 필요합니다.
 */
app.use('/api/user', userRouter);
app.use('/api/patient', patientRouter);
app.use('/api/medication', medicationRouter);
app.use('/api/schedule', scheduleRouter);
app.use('/api/dashboard', dashboardRouter);
app.use('/api/device', deviceRouter);
app.use('/api/face-data', faceDataRouter);
app.use('/api/notification', notificationRouter);
app.use('/api/log', logRouter);



https.createServer(sslOptions, app).listen(PORT, () => {
    console.log(`Care-full 서버가 ${PORT}번 포트에서 실행 중입니다.`);
});

process.on('SIGINT', async () => {
    console.log('서버를 종료합니다. DB 연결을 정리합니다.');
    await pool.end();
    process.exit(0);
});
