const express = require('express');
const router  = express.Router();
const path    = require('path');
const fs      = require('fs');
const multer  = require('multer');

const pool            = require('../db');
const { verifyToken } = require('../middleware/auth');
const { sendSuccess, sendError } = require('../utils/response');
const elevenlabs      = require('../services/elevenlabs.service');

// ─── 업로드 디렉터리 ───────────────────────────────────────────────────────────
const UPLOAD_DIR = path.join(__dirname, '..', 'uploads', 'voices');
fs.mkdirSync(UPLOAD_DIR, { recursive: true });

const MAX_BYTES = 10 * 1024 * 1024; // 10 MB

// ─── Multer 설정 ───────────────────────────────────────────────────────────────
const storage = multer.diskStorage({
    destination: (_req, _file, cb) => cb(null, UPLOAD_DIR),
    filename: (req, file, cb) => {
        const ext = path.extname(file.originalname) || '.webm';
        cb(null, `voice_${req.user.mem_id}_${Date.now()}${ext}`);
    },
});

const upload = multer({
    storage,
    limits: { fileSize: MAX_BYTES },
    fileFilter: (_req, file, cb) => {
        if (file.mimetype.startsWith('audio/')) return cb(null, true);
        cb(new Error('오디오 파일만 업로드할 수 있습니다'));
    },
});

// ─── 서버 간 콜백 인증 ────────────────────────────────────────────────────────
function verifyCallbackSecret(req, res, next) {
    const secret = process.env.VOICE_CALLBACK_SECRET;
    if (secret && req.headers['x-callback-secret'] !== secret) {
        return sendError(res, 401, '인증되지 않은 요청입니다');
    }
    next();
}

// ─── 공통 헬퍼 ────────────────────────────────────────────────────────────────
async function get_patient_id(mem_id) {
    const { rows } = await pool.query(
        'SELECT patient_id FROM patients WHERE mem_id = $1 AND deleted_at IS NULL LIMIT 1',
        [mem_id]
    );
    return rows[0]?.patient_id ?? null;
}

function remove_file(file_path) {
    try {
        const abs = path.isAbsolute(file_path)
            ? file_path
            : path.join(__dirname, '..', file_path);
        if (fs.existsSync(abs)) fs.unlinkSync(abs);
    } catch (e) {
        console.warn('[voice] 파일 삭제 실패:', e.message);
    }
}

async function delete_patient_voices(patient_id) {
    const { rows } = await pool.query(
        'SELECT file_path, elevenlabs_voice_id FROM voice_samples WHERE patient_id = $1',
        [patient_id]
    );
    for (const r of rows) {
        remove_file(r.file_path);
        if (r.elevenlabs_voice_id) {
            elevenlabs.delete_voice(r.elevenlabs_voice_id).catch(
                (e) => console.warn('[voice] ElevenLabs 보이스 삭제 실패:', e.message)
            );
        }
    }
    await pool.query('DELETE FROM voice_samples WHERE patient_id = $1', [patient_id]);
}

// ─── GET /api/voice ───────────────────────────────────────────────────────────
// 현재 등록된 목소리 조회
router.get('/', verifyToken, async (req, res) => {
    try {
        const patient_id = await get_patient_id(req.user.mem_id);
        if (!patient_id) return sendError(res, 404, '환자 정보를 찾을 수 없습니다');

        const { rows } = await pool.query(
            `SELECT voice_id, file_name, file_size, mime_type, status, uploaded_at
             FROM voice_samples
             WHERE patient_id = $1
             ORDER BY uploaded_at DESC
             LIMIT 1`,
            [patient_id]
        );

        return sendSuccess(res, 200, { voice: rows[0] ?? null });
    } catch (err) {
        console.error('[GET /api/voice]', err);
        return sendError(res, 500, '서버 오류가 발생했습니다');
    }
});

// ─── POST /api/voice/upload ───────────────────────────────────────────────────
// 목소리 파일 업로드 (기존 파일 대체)
router.post('/upload', verifyToken, upload.single('voice'), async (req, res) => {
    if (!req.file) return sendError(res, 400, '업로드된 파일이 없습니다');

    let patient_id;
    try {
        patient_id = await get_patient_id(req.user.mem_id);
        if (!patient_id) {
            remove_file(req.file.path);
            return sendError(res, 404, '환자 정보를 찾을 수 없습니다');
        }

        // 기존 목소리 파일·레코드 삭제
        await delete_patient_voices(patient_id);

        // 새 레코드 저장 (file_path는 uploads/voices/... 상대 경로)
        const relative_path = path.join('uploads', 'voices', req.file.filename);
        const { rows } = await pool.query(
            `INSERT INTO voice_samples
               (patient_id, file_name, file_path, file_size, mime_type, status)
             VALUES ($1, $2, $3, $4, $5, 'pending')
             RETURNING voice_id, file_name, file_size, mime_type, status, uploaded_at`,
            [
                patient_id,
                req.file.originalname,
                relative_path,
                req.file.size,
                req.file.mimetype,
            ]
        );

        const saved_voice = rows[0];
        // 응답 먼저 반환 (ElevenLabs는 시간이 걸리므로 비동기 처리)
        res.status(201).json({ success: true, voice: saved_voice });

        // ── ElevenLabs 파이프라인 (백그라운드) ──────────────────────────────
        _run_elevenlabs_pipeline(saved_voice.voice_id, req.file.path, patient_id).catch(
            (e) => console.error('[voice] ElevenLabs 파이프라인 실패:', e.message)
        );

    } catch (err) {
        if (req.file) remove_file(req.file.path);
        console.error('[POST /api/voice/upload]', err);
        return sendError(res, 500, '업로드 중 오류가 발생했습니다');
    }
});

/**
 * 업로드 완료 후 백그라운드에서 실행:
 *  1) ElevenLabs 보이스 클로닝
 *  2) 고정 메시지 TTS 생성
 *  3) alarm 파일로 저장 + devices 테이블 갱신
 *  4) voice_samples 상태 업데이트
 */
async function _run_elevenlabs_pipeline(voice_id, audio_abs_path, patient_id) {
    const SOUNDS_DIR = path.join(__dirname, '..', 'uploads', 'sounds');
    fs.mkdirSync(SOUNDS_DIR, { recursive: true });

    try {
        // 1. 보이스 클로닝
        console.log(`[voice] ElevenLabs 클로닝 시작 voice_id=${voice_id}`);
        const el_voice_id = await elevenlabs.clone_voice(
            audio_abs_path,
            `carefull_patient_${patient_id}`
        );
        console.log(`[voice] 클로닝 완료 el_voice_id=${el_voice_id}`);

        // 2. TTS 생성 → uploads/sounds/alarm_{voice_id}.mp3
        const filename    = `alarm_voice_${voice_id}.mp3`;
        const output_abs  = path.join(SOUNDS_DIR, filename);
        await elevenlabs.text_to_speech(el_voice_id, output_abs);
        console.log(`[voice] TTS 생성 완료 → ${filename}`);

        // 3. voice_samples 갱신
        const relative_sound = path.join('uploads', 'sounds', filename);
        await pool.query(
            `UPDATE voice_samples
             SET elevenlabs_voice_id = $1,
                 status              = 'ready',
                 updated_at          = NOW()
             WHERE voice_id = $2`,
            [el_voice_id, voice_id]
        );

        // 4. 환자 기기의 alarm_sound 갱신 (라즈베리 sync 대상)
        await pool.query(
            `UPDATE devices
             SET alarm_sound_path       = $1,
                 alarm_sound_name       = $2,
                 alarm_sound_updated_at = NOW()
             WHERE patient_id = $3`,
            [relative_sound, filename, patient_id]
        );

        console.log(`[voice] 파이프라인 완료 patient_id=${patient_id}`);

    } catch (err) {
        remove_file(audio_abs_path);
        await pool.query(
            `UPDATE voice_samples SET status = 'error', updated_at = NOW() WHERE voice_id = $1`,
            [voice_id]
        );
        throw err;
    }
}

// ─── DELETE /api/voice ────────────────────────────────────────────────────────
// 등록된 목소리 삭제
router.delete('/', verifyToken, async (req, res) => {
    try {
        const patient_id = await get_patient_id(req.user.mem_id);
        if (!patient_id) return sendError(res, 404, '환자 정보를 찾을 수 없습니다');

        const { rowCount } = await pool.query(
            'SELECT 1 FROM voice_samples WHERE patient_id = $1 LIMIT 1',
            [patient_id]
        );
        if (!rowCount) return sendError(res, 404, '등록된 목소리가 없습니다');

        await delete_patient_voices(patient_id);
        return sendSuccess(res, 200, { message: '목소리가 삭제되었습니다' });
    } catch (err) {
        console.error('[DELETE /api/voice]', err);
        return sendError(res, 500, '서버 오류가 발생했습니다');
    }
});

// ─── PATCH /api/voice/status ──────────────────────────────────────────────────
// AI 처리 결과 상태 업데이트 (AI 서버 → 백엔드 콜백용)
router.patch('/status', verifyCallbackSecret, async (req, res) => {
    const { voice_id, status } = req.body;
    const allowed = ['pending', 'processing', 'ready', 'error'];
    if (!voice_id || !allowed.includes(status)) {
        return sendError(res, 400, 'voice_id와 유효한 status가 필요합니다');
    }
    try {
        const { rowCount } = await pool.query(
            `UPDATE voice_samples SET status = $1, updated_at = NOW() WHERE voice_id = $2`,
            [status, voice_id]
        );
        if (!rowCount) return sendError(res, 404, '해당 voice_id를 찾을 수 없습니다');
        return sendSuccess(res, 200, { message: '상태가 업데이트되었습니다' });
    } catch (err) {
        console.error('[PATCH /api/voice/status]', err);
        return sendError(res, 500, '서버 오류가 발생했습니다');
    }
});

module.exports = router;
