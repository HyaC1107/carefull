const express = require('express');
const axios = require('axios');
const jwt = require('jsonwebtoken');

const router = express.Router();
const pool = require('../db');
const { verifyToken } = require('../middleware/auth');

const {
    JWT_SECRET,
    KAKAO_CLIENT_ID,
    KAKAO_CLIENT_SECRET,
    KAKAO_REDIRECT_URI,
    GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET,
    GOOGLE_REDIRECT_URI,
    NAVER_CLIENT_ID,
    NAVER_CLIENT_SECRET,
    NAVER_REDIRECT_URI
} = process.env;

/**
 * 소셜 로그인 공통 처리
 *
 * 왜 수정했는가:
 * - verifyToken에서 req.user.memberId를 기준으로 통일했기 때문에
 *   JWT 발급 시 payload 키도 memberId로 유지해야 전체 인증 흐름이 맞습니다.
 */
const handleSocialLogin = async (socialData, provider, res) => {
    try {
        const findQuery = `
            SELECT member_id, nickname
            FROM members
            WHERE social_id = $1 AND provider = $2
        `;
        const result = await pool.query(findQuery, [socialData.id, provider]);

        let memberId;
        let nickname;
        let isNewUser = false;

        if (result.rows.length === 0) {
            isNewUser = true;

            const insertQuery = `
                INSERT INTO members (social_id, provider, email, nickname)
                VALUES ($1, $2, $3, $4)
                RETURNING member_id, nickname
            `;
            const newUser = await pool.query(insertQuery, [
                socialData.id,
                provider,
                socialData.email,
                socialData.nickname
            ]);

            memberId = newUser.rows[0].member_id;
            nickname = newUser.rows[0].nickname;
        } else {
            memberId = result.rows[0].member_id;
            nickname = result.rows[0].nickname;
        }

        const accessToken = jwt.sign(
            { memberId, nickname },
            JWT_SECRET,
            { expiresIn: '2h' }
        );

        return res.status(200).json({
            success: true,
            token: accessToken,
            isNewUser,
            nextStep: isNewUser ? '/register-patient' : '/main',
            userData: {
                memberId,
                nickname,
                provider
            }
        });
    } catch (error) {
        console.error(`${provider} 로그인 처리 중 오류가 발생했습니다:`, error);
        return res.status(500).json({
            success: false,
            message: '소셜 로그인 처리 중 서버 오류가 발생했습니다.'
        });
    }
};

router.get('/callback', async (req, res) => {
    try {
        const tokenResponse = await axios.post(
            'https://kauth.kakao.com/oauth/token',
            new URLSearchParams({
                grant_type: 'authorization_code',
                client_id: KAKAO_CLIENT_ID,
                client_secret: KAKAO_CLIENT_SECRET,
                redirect_uri: KAKAO_REDIRECT_URI,
                code: req.query.code
            }),
            {
                headers: {
                    'Content-type': 'application/x-www-form-urlencoded'
                }
            }
        );

        const userResponse = await axios.get('https://kapi.kakao.com/v2/user/me', {
            headers: {
                Authorization: `Bearer ${tokenResponse.data.access_token}`
            }
        });

        return handleSocialLogin({
            id: userResponse.data.id.toString(),
            nickname: userResponse.data.properties.nickname,
            email: userResponse.data.kakao_account.email || null
        }, 'kakao', res);
    } catch (error) {
        return res.status(500).json({
            success: false,
            message: '카카오 인증 처리 중 오류가 발생했습니다.'
        });
    }
});

router.get('/google/callback', async (req, res) => {
    try {
        const tokenResponse = await axios.post('https://oauth2.googleapis.com/token', {
            code: req.query.code,
            client_id: GOOGLE_CLIENT_ID,
            client_secret: GOOGLE_CLIENT_SECRET,
            redirect_uri: GOOGLE_REDIRECT_URI,
            grant_type: 'authorization_code'
        });

        const userResponse = await axios.get(
            'https://www.googleapis.com/oauth2/v3/userinfo',
            {
                headers: {
                    Authorization: `Bearer ${tokenResponse.data.access_token}`
                }
            }
        );

        return handleSocialLogin({
            id: userResponse.data.sub,
            nickname: userResponse.data.name,
            email: userResponse.data.email
        }, 'google', res);
    } catch (error) {
        return res.status(500).json({
            success: false,
            message: '구글 인증 처리 중 오류가 발생했습니다.'
        });
    }
});

router.get('/naver/callback', async (req, res) => {
    try {
        const tokenResponse = await axios.get('https://nid.naver.com/oauth2.0/token', {
            params: {
                grant_type: 'authorization_code',
                client_id: NAVER_CLIENT_ID,
                client_secret: NAVER_CLIENT_SECRET,
                code: req.query.code,
                state: req.query.state
            }
        });

        const userResponse = await axios.get('https://openapi.naver.com/v1/nid/me', {
            headers: {
                Authorization: `Bearer ${tokenResponse.data.access_token}`
            }
        });

        const { response } = userResponse.data;

        return handleSocialLogin({
            id: response.id,
            nickname: response.nickname,
            email: response.email
        }, 'naver', res);
    } catch (error) {
        return res.status(500).json({
            success: false,
            message: '네이버 인증 처리 중 오류가 발생했습니다.'
        });
    }
});

/**
 * 개발용 mock 소셜 로그인 API
 *
 * 왜 추가했는가:
 * - 실제 OAuth 인증 없이도 신규 회원가입 / 기존 회원 로그인 흐름을 테스트하기 위함입니다.
 * - members 테이블에서 social_id + provider 기준으로 기존 회원을 찾고,
 *   없으면 새로 생성한 뒤 실제 소셜 로그인과 같은 형식의 JWT를 발급합니다.
 */
router.post('/dev-login', async (req, res) => {
    const { social_id, provider, nickname, email } = req.body;

    if (!social_id || !provider || !nickname) {
        return res.status(400).json({
            success: false,
            message: 'social_id, provider, nickname은 필수입니다.'
        });
    }

    return handleSocialLogin({
        id: String(social_id),
        nickname,
        email: email || null
    }, provider, res);
});

/**
 * 기존 환자 등록 API
 *
 * 왜 수정했는가:
 * - verifyToken의 표준 사용자 식별자를 req.user.memberId로 고정했기 때문에
 *   이 라우트도 같은 키만 사용하도록 유지합니다.
 * - req.user.member_id 같은 다른 키는 현재 워크스페이스에서 확인되지 않았습니다.
 */
router.post('/register-patient', verifyToken, async (req, res) => {
    const memberId = req.user.memberId;
    const { name, birth_date, gender, blood_type, height, weight, serial_number } = req.body;
    const client = await pool.connect();

    try {
        await client.query('BEGIN');

        const userRes = await client.query(
            `
                INSERT INTO users (member_id, name, birth_date, gender, blood_type, height, weight)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                RETURNING user_id
            `,
            [memberId, name, birth_date, gender, blood_type, height, weight]
        );
        const userId = userRes.rows[0].user_id;

        const deviceRes = await client.query(
            `
                UPDATE devices
                SET user_id = $1, status = 'REGISTERED', registered_at = CURRENT_TIMESTAMP
                WHERE serial_number = $2
                RETURNING device_id
            `,
            [userId, serial_number]
        );

        if (deviceRes.rows.length === 0) {
            throw new Error('등록되지 않은 기기 시리얼 번호입니다.');
        }

        await client.query('COMMIT');

        return res.status(200).json({
            success: true,
            message: '환자 및 기기 등록이 완료되었습니다.',
            userId
        });
    } catch (error) {
        await client.query('ROLLBACK');
        console.error('환자 등록 중 오류가 발생했습니다:', error);

        return res.status(400).json({
            success: false,
            message: error.message
        });
    } finally {
        client.release();
    }
});

module.exports = router;
