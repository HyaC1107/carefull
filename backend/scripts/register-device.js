/**
 * 기기 등록 스크립트 (patient 연결 없이 device_uid만 등록)
 * 사용법: node scripts/register-device.js <device_uid>
 * 예시:   node scripts/register-device.js 1107
 */

require('dotenv').config({ path: require('path').resolve(__dirname, '../.env') });

const pool = require('../db');

async function main() {
    const [,, device_uid] = process.argv;

    if (!device_uid) {
        console.error('사용법: node scripts/register-device.js <device_uid>');
        process.exit(1);
    }

    try {
        const { rows: existing } = await pool.query(
            'SELECT device_id FROM devices WHERE device_uid = $1', [device_uid.trim()]
        );

        let rows;
        if (existing.length > 0) {
            ({ rows } = await pool.query(
                `UPDATE devices SET device_status = 'REGISTERED', last_ping = NOW()
                 WHERE device_uid = $1
                 RETURNING device_id, device_uid, patient_id, device_status, registered_at`,
                [device_uid.trim()]
            ));
            console.log('기존 기기 업데이트 완료:', rows[0]);
        } else {
            ({ rows } = await pool.query(
                `INSERT INTO devices (device_uid, device_status, registered_at, last_ping, device_name)
                 VALUES ($1, 'REGISTERED', NOW(), NOW(), 'TEST_DEVICE')
                 RETURNING device_id, device_uid, patient_id, device_status, registered_at`,
                [device_uid.trim()]
            ));
            console.log('기기 등록 완료:', rows[0]);
        }
    } catch (err) {
        console.error('오류:', err.message);
    } finally {
        await pool.end();
    }
}

main();
