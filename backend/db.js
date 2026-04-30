require('dotenv').config();
const { Pool } = require('pg');

const required = ['DB_HOST', 'DB_USER', 'DB_PASSWORD', 'DB_NAME', 'DB_PORT'];
for (const key of required) {
    if (!process.env[key]) throw new Error(`Missing env variable: ${key}`);
}

const pool = new Pool({
    host:     process.env.DB_HOST,
    user:     process.env.DB_USER,
    password: process.env.DB_PASSWORD,
    database: process.env.DB_NAME,
    port:     Number(process.env.DB_PORT),
    max:                 20,
    idleTimeoutMillis:   30_000,
    connectionTimeoutMillis: 5_000,
});

pool.query('SELECT NOW()', (err) => {
    if (err) {
        console.error('❌ DB 연결 실패:', err.message);
    }
});

module.exports = pool;
