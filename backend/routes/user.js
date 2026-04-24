const express = require('express');
const axios = require('axios');
const jwt = require('jsonwebtoken');

const router = express.Router();
const pool = require('../db');
const { verifyToken } = require('../middleware/auth');

const {
    JWT_SECRET,
    FRONTEND_URL,
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

if (!FRONTEND_URL) throw new Error('Missing env variable: FRONTEND_URL');
const RESOLVED_FRONTEND_URL = FRONTEND_URL;

const build_kakao_authorize_url = () => {
    const params = new URLSearchParams({
        client_id: KAKAO_CLIENT_ID,
        redirect_uri: KAKAO_REDIRECT_URI,
        response_type: 'code',
        prompt: 'select_account'
    });

    return `https://kauth.kakao.com/oauth/authorize?${params.toString()}`;
};

const build_google_authorize_url = () => {
    const params = new URLSearchParams({
        client_id: GOOGLE_CLIENT_ID,
        redirect_uri: GOOGLE_REDIRECT_URI,
        response_type: 'code',
        scope: 'email profile',
        prompt: 'select_account'
    });

    return `https://accounts.google.com/o/oauth2/v2/auth?${params.toString()}`;
};

const build_naver_authorize_url = () => {
    const params = new URLSearchParams({
        response_type: 'code',
        client_id: NAVER_CLIENT_ID,
        redirect_uri: NAVER_REDIRECT_URI,
        state: `carefull_${Date.now()}`
    });

    return `https://nid.naver.com/oauth2.0/authorize?${params.toString()}`;
};

const build_frontend_callback_url = ({ provider, token, is_new_user, error }) => {
    const callback_url = new URL(`/login/callback/${provider}`, RESOLVED_FRONTEND_URL);

    callback_url.searchParams.set('provider', provider);

    if (token) {
        callback_url.searchParams.set('token', token);
    }

    if (typeof is_new_user === 'boolean') {
        callback_url.searchParams.set('is_new_user', String(is_new_user));
    }

    if (error) {
        callback_url.searchParams.set('error', error);
    }

    return callback_url.toString();
};

const handle_social_login = async (social_data, provider) => {
    try {
        const find_query = `
            SELECT mem_id, nick
            FROM members
            WHERE social_id = $1 AND provider = $2
        `;
        const result = await pool.query(find_query, [social_data.id, provider]);

        let mem_id;
        let nick;
        let is_new_user = false;

        if (result.rows.length === 0) {
            is_new_user = true;

            const insert_query = `
                INSERT INTO members (social_id, provider, email, nick, profile_img)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING mem_id, nick
            `;
            const new_user = await pool.query(insert_query, [
                social_data.id,
                provider,
                social_data.email || '',
                social_data.nickname,
                social_data.profile_img || ''
            ]);

            mem_id = new_user.rows[0].mem_id;
            nick = new_user.rows[0].nick;
        } else {
            mem_id = result.rows[0].mem_id;
            nick = result.rows[0].nick;
        }

        const access_token = jwt.sign(
            { mem_id, nick },
            JWT_SECRET,
            { expiresIn: '2h' }
        );

        return {
            success: true,
            token: access_token,
            is_new_user,
            next_step: is_new_user ? '/register-patient' : '/main',
            user_data: {
                mem_id,
                nick,
                provider
            }
        };
    } catch (error) {
        console.error(`${provider} login error:`, error);
        return {
            success: false,
            message: 'Server error while processing social login.'
        };
    }
};

router.get('/kakao', (req, res) => {
    return res.redirect(build_kakao_authorize_url());
});

router.get('/google', (req, res) => {
    return res.redirect(build_google_authorize_url());
});

router.get('/naver', (req, res) => {
    return res.redirect(build_naver_authorize_url());
});

router.get('/callback', async (req, res) => {
    try {
        const token_response = await axios.post(
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

        const user_response = await axios.get('https://kapi.kakao.com/v2/user/me', {
            headers: {
                Authorization: `Bearer ${token_response.data.access_token}`
            }
        });

        const login_result = await handle_social_login({
            id: user_response.data.id.toString(),
            nickname: user_response.data.properties.nickname,
            email: user_response.data.kakao_account.email || null,
            profile_img: user_response.data.properties.profile_image || null
        }, 'kakao');

        if (!login_result.success || !login_result.token) {
            return res.redirect(build_frontend_callback_url({
                provider: 'kakao',
                error: login_result.message || 'Kakao authentication failed.'
            }));
        }

        return res.redirect(build_frontend_callback_url({
            provider: 'kakao',
            token: login_result.token,
            is_new_user: login_result.is_new_user
        }));
    } catch (error) {
        return res.redirect(build_frontend_callback_url({
            provider: 'kakao',
            error: 'Kakao authentication failed.'
        }));
    }
});

router.get('/google/callback', async (req, res) => {
    try {
        const token_response = await axios.post('https://oauth2.googleapis.com/token', {
            code: req.query.code,
            client_id: GOOGLE_CLIENT_ID,
            client_secret: GOOGLE_CLIENT_SECRET,
            redirect_uri: GOOGLE_REDIRECT_URI,
            grant_type: 'authorization_code'
        });

        const user_response = await axios.get(
            'https://www.googleapis.com/oauth2/v3/userinfo',
            {
                headers: {
                    Authorization: `Bearer ${token_response.data.access_token}`
                }
            }
        );

        const login_result = await handle_social_login({
            id: user_response.data.sub,
            nickname: user_response.data.name,
            email: user_response.data.email,
            profile_img: user_response.data.picture || null
        }, 'google');

        if (!login_result.success || !login_result.token) {
            return res.redirect(build_frontend_callback_url({
                provider: 'google',
                error: login_result.message || 'Google authentication failed.'
            }));
        }

        return res.redirect(build_frontend_callback_url({
            provider: 'google',
            token: login_result.token,
            is_new_user: login_result.is_new_user
        }));
    } catch (error) {
        return res.redirect(build_frontend_callback_url({
            provider: 'google',
            error: 'Google authentication failed.'
        }));
    }
});

router.get('/naver/callback', async (req, res) => {
    try {
        const token_response = await axios.get('https://nid.naver.com/oauth2.0/token', {
            params: {
                grant_type: 'authorization_code',
                client_id: NAVER_CLIENT_ID,
                client_secret: NAVER_CLIENT_SECRET,
                code: req.query.code,
                state: req.query.state
            }
        });

        const user_response = await axios.get('https://openapi.naver.com/v1/nid/me', {
            headers: {
                Authorization: `Bearer ${token_response.data.access_token}`
            }
        });

        const { response } = user_response.data;

        const login_result = await handle_social_login({
            id: response.id,
            nickname: response.nickname,
            email: response.email,
            profile_img: response.profile_image || null
        }, 'naver');

        if (!login_result.success || !login_result.token) {
            return res.redirect(build_frontend_callback_url({
                provider: 'naver',
                error: login_result.message || 'Naver authentication failed.'
            }));
        }

        return res.redirect(build_frontend_callback_url({
            provider: 'naver',
            token: login_result.token,
            is_new_user: login_result.is_new_user
        }));
    } catch (error) {
        return res.redirect(build_frontend_callback_url({
            provider: 'naver',
            error: 'Naver authentication failed.'
        }));
    }
});

router.post('/dev-login', async (req, res) => {
    const { social_id, provider, nick, nickname, email } = req.body;
    const resolved_nick = nick || nickname;

    if (!social_id || !provider || !resolved_nick) {
        return res.status(400).json({
            success: false,
            message: 'social_id, provider, and nick are required.'
        });
    }

    const login_result = await handle_social_login({
        id: String(social_id),
        nickname: resolved_nick,
        email: email || '',
        profile_img: ''
    }, provider);

    if (!login_result.success) {
        return res.status(500).json(login_result);
    }

    return res.status(200).json(login_result);
});

router.post('/register-patient', verifyToken, async (req, res) => {
    const mem_id = req.user.mem_id;
    const {
        patient_name,
        birthdate,
        gender,
        bloodtype,
        height,
        weight,
        device_uid,
        deviceName,
        device_name
    } = req.body;
    const normalized_device_name = String(device_name || deviceName || '').trim();
    const client = await pool.connect();

    try {
        await client.query('BEGIN');

        const patient_result = await client.query(
            `
                INSERT INTO patients (
                    mem_id,
                    patient_name,
                    birthdate,
                    gender,
                    bloodtype,
                    height,
                    weight,
                    phone,
                    address,
                    fingerprint_id,
                    guardian_name,
                    guardian_phone
                )
                VALUES (
                    $1, $2, $3, $4, $5, $6, $7,
                    '', '', 0, '', ''
                )
                RETURNING patient_id
            `,
            [mem_id, patient_name, birthdate, gender, bloodtype, height, weight]
        );
        const patient_id = patient_result.rows[0].patient_id;

        const device_result = await client.query(
            `
                UPDATE devices
                SET
                    patient_id = $1,
                    device_status = 'REGISTERED',
                    registered_at = CURRENT_TIMESTAMP,
                    last_ping = CURRENT_TIMESTAMP,
                    device_name = COALESCE(NULLIF($3, ''), device_name, 'UNKNOWN')
                WHERE device_uid = $2
                RETURNING device_id
            `,
            [patient_id, device_uid, normalized_device_name]
        );

        if (device_result.rows.length === 0) {
            throw new Error('Registered device not found.');
        }

        await client.query('COMMIT');

        return res.status(200).json({
            success: true,
            message: 'Patient and device registration completed.',
            patient_id
        });
    } catch (error) {
        await client.query('ROLLBACK');
        console.error('Patient registration error:', error);

        return res.status(400).json({
            success: false,
            message: error.message
        });
    } finally {
        client.release();
    }
});

module.exports = router;
