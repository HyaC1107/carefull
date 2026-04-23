require('dotenv').config();

const express = require('express');
const https = require('https');
const fs = require('fs');
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

startMissedLogJob();

const app = express();
const port = 443;
const frontend_dist_path = path.resolve(__dirname, '../frontend/dist');
const frontend_index_path = path.join(frontend_dist_path, 'index.html');

app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

app.use(express.static(path.join(__dirname, 'public')));
app.use('/uploads', express.static(path.join(__dirname, 'uploads')));
app.use(express.static(frontend_dist_path));

const ssl_options = {
    key: fs.readFileSync(path.join(__dirname, '192.168.219.225.nip.io-key.pem')),
    cert: fs.readFileSync(path.join(__dirname, '192.168.219.225.nip.io.pem'))
};

app.use('/api/user', user_router);
app.use('/api/patient', patient_router);
app.use('/api/medication', medication_router);
app.use('/api/schedule', schedule_router);
app.use('/api/dashboard', dashboard_router);
app.use('/api/device', device_router);
app.use('/api/face-data', face_data_router);
app.use('/api/notification', notification_router);
app.use('/api/log', activity_router);
app.get(/^(?!\/api|\/uploads).*/, (req, res) => {
    res.sendFile(frontend_index_path);
});

https.createServer(ssl_options, app).listen(port, () => {
    console.log(`Care-full server is running on port ${port}.`);
});

process.on('SIGINT', async () => {
    console.log('Shutting down server and closing DB connections.');
    await pool.end();
    process.exit(0);
});
