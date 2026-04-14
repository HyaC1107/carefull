// [1] 필수 모듈 임포트
const { Pool } = require('pg'); // PostgreSQL 연결을 위한 풀(Pool) 모듈
require('dotenv').config(); // .env 파일의 변수들을 process.env로 불러옴

// [2] DB 연결 설정
// 이제 모든 정보는 .env 파일에서 가져오게 돼!
const dbConfig = {
    host: process.env.DB_HOST,
    user: process.env.DB_USER,
    password: process.env.DB_PASSWORD,
    database: process.env.DB_NAME,
    port: Number(process.env.DB_PORT), // 포트는 반드시 숫자로 변환해야 함
};

// [3] Pool 객체 생성
// 연결 설정을 바탕으로 DB와 통신할 통로를 만들어
const pool = new Pool(dbConfig);

// [4] 모듈 수출
// 다른 파일(라우터 등)에서 DB를 쓸 수 있게 내보내기
module.exports = pool;

// db.js 맨 아래에 추가해봐!
pool.query('SELECT NOW()', (err, res) => {
    if (err) {
        console.error('❌ DB 연결 실패, 랑랑! 설정 확인해봐:', err);
    } else {
        console.log('✅ DB 연결 성공! 현재 시간:', res.rows[0].now);
    }
});