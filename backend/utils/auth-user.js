const pool = require('../db');

/**
 * 현재 로그인한 memberId로 users 테이블의 user_id를 찾습니다.
 *
 * 왜 필요한가:
 * - JWT에서는 memberId를 사용하지만,
 *   실제 환자/기기/일정 관련 테이블은 user_id를 기준으로 연결됩니다.
 * - 따라서 라우트에서 반복되던 변환 로직을 공통 유틸로 분리합니다.
 */
const findUserIdByMemberId = async (memberId) => {
    const query = `
        SELECT user_id
        FROM users
        WHERE member_id = $1
        LIMIT 1
    `;

    const { rows } = await pool.query(query, [memberId]);
    return rows.length > 0 ? rows[0].user_id : null;
};

module.exports = {
    findUserIdByMemberId
};
