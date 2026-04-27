// PM2 설정 — 부팅 시 자동 실행
// 사용법:
//   pm2 start ecosystem.config.js
//   pm2 save
//   pm2 startup   ← 출력된 sudo 명령 복사해서 실행

const path = require('path');
const HOME = process.env.HOME || '/home/pi';

module.exports = {
  apps: [
    {
      name: 'carefull',
      script: './run.sh',
      interpreter: '/bin/bash',
      cwd: __dirname,           // ecosystem.config.js 위치 = raspberry/
      env: {
        DISPLAY: ':0',
        XAUTHORITY: `${HOME}/.Xauthority`,
        CAREFULL_FULLSCREEN: '1',
      },
      autorestart: true,
      restart_delay: 5000,      // 재시작 전 5초 대기
      max_restarts: 10,
      watch: false,             // PM2 자체 watch는 끔 (dev_watch.py 사용)
      log_date_format: 'YYYY-MM-DD HH:mm:ss',
    },
  ],
};
