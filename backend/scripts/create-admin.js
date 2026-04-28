/**
 * 관리자 계정 생성 스크립트
 * 사용법: node scripts/create-admin.js <login_id> <password> <name> [role]
 * 예시:   node scripts/create-admin.js admin01 mypassword 홍길동 super_admin
 */

require('dotenv').config({ path: require('path').resolve(__dirname, '../.env') });

const bcrypt = require('bcryptjs');
const pool   = require('../db');

async function main() {
    const [,, login_id, password, name, role = 'admin'] = process.argv;

    if (!login_id || !password || !name) {
        console.error('사용법: node scripts/create-admin.js <login_id> <password> <name> [role]');
        process.exit(1);
    }

    const hashed = await bcrypt.hash(password, 10);

    try {
        const { rows } = await pool.query(
            `INSERT INTO admins (login_id, password, name, role)
             VALUES ($1, $2, $3, $4)
             ON CONFLICT (login_id) DO NOTHING
             RETURNING admin_id, login_id, name, role`,
            [login_id, hashed, name, role]
        );

        if (rows.length === 0) {
            console.log(`이미 존재하는 login_id: ${login_id}`);
        } else {
            console.log('관리자 계정 생성 완료:', rows[0]);
        }
    } catch (err) {
        console.error('오류:', err.message);
    } finally {
        await pool.end();
    }
}

main();
