const express = require('express');
const router  = express.Router();
const path    = require('path');
const fs      = require('fs');

const pool            = require('../db');
const { verifyToken } = require('../middleware/auth');
const { sendSuccess, sendError } = require('../utils/response');
const elevenlabs      = require('../services/elevenlabs.service');

// ─── 디렉터리 ─────────────────────────────────────────────────────────────────
const SOUNDS_DIR   = path.join(__dirname, '..', 'uploads', 'sounds');
const PREVIEWS_DIR = path.join(__dirname, '..', 'uploads', 'previews');
fs.mkdirSync(SOUNDS_DIR,   { recursive: true });
fs.mkdirSync(PREVIEWS_DIR, { recursive: true });

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
        'SELECT file_path FROM voice_samples WHERE patient_id = $1',
        [patient_id]
    );
    for (const r of rows) {
        if (r.file_path) remove_file(r.file_path);
    }
    await pool.query('DELETE FROM voice_samples WHERE patient_id = $1', [patient_id]);
}

// ─── GET /api/voice/voices ────────────────────────────────────────────────────
// ElevenLabs 기성 목소리 목록
router.get('/voices', verifyToken, async (req, res) => {
    try {
        const voices = await elevenlabs.get_voices();
        return sendSuccess(res, 200, { voices });
    } catch (err) {
        console.error('[GET /api/voice/voices]', err.message);
        return sendError(res, 502, 'ElevenLabs 목소리 목록을 가져오지 못했습니다');
    }
});

// ─── GET /api/voice ───────────────────────────────────────────────────────────
// 현재 등록된 TTS 설정 조회
router.get('/', verifyToken, async (req, res) => {
    try {
        const patient_id = await get_patient_id(req.user.mem_id);
        if (!patient_id) return sendError(res, 404, '환자 정보를 찾을 수 없습니다');

        const { rows } = await pool.query(
            `SELECT voice_id, file_name, file_size, mime_type, status, uploaded_at, updated_at
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

// ─── POST /api/voice/preview ──────────────────────────────────────────────────
// 미리듣기용 TTS 임시 생성 → URL 반환
router.post('/preview', verifyToken, async (req, res) => {
    const { voice_id, text } = req.body;
    if (!voice_id) return sendError(res, 400, 'voice_id가 필요합니다');
    if (!text || !text.trim()) return sendError(res, 400, 'text가 필요합니다');
    if (text.length > 300) return sendError(res, 400, '텍스트는 300자 이하여야 합니다');

    try {
        const filename    = `preview_${req.user.mem_id}_${Date.now()}.mp3`;
        const output_path = path.join(PREVIEWS_DIR, filename);

        await elevenlabs.generate_tts(voice_id, text.trim(), output_path);

        // 10분 후 임시 파일 자동 삭제
        setTimeout(() => remove_file(output_path), 10 * 60 * 1000);

        return sendSuccess(res, 200, { url: `/api/voice/preview-file/${filename}` });
    } catch (err) {
        console.error('[POST /api/voice/preview]', err.message);
        return sendError(res, 502, 'TTS 생성에 실패했습니다. 잠시 후 다시 시도해주세요.');
    }
});

// ─── GET /api/voice/preview-file/:filename ────────────────────────────────────
// 생성된 미리듣기 MP3 파일 서빙
router.get('/preview-file/:filename', verifyToken, (req, res) => {
    const { filename } = req.params;
    // 경로 탐색 방지
    if (filename.includes('/') || filename.includes('..')) {
        return sendError(res, 400, '잘못된 파일 이름입니다');
    }
    const file_path = path.join(PREVIEWS_DIR, filename);
    if (!fs.existsSync(file_path)) {
        return sendError(res, 404, '미리듣기 파일이 만료되었습니다. 다시 생성해주세요.');
    }
    res.setHeader('Content-Type', 'audio/mpeg');
    res.sendFile(file_path);
});

// ─── POST /api/voice/generate ─────────────────────────────────────────────────
// 보호자가 선택한 목소리 + 텍스트로 TTS 생성 → 기기 알림음으로 저장
router.post('/generate', verifyToken, async (req, res) => {
    const { voice_id, voice_name, text } = req.body;
    if (!voice_id)             return sendError(res, 400, 'voice_id가 필요합니다');
    if (!text || !text.trim()) return sendError(res, 400, 'text가 필요합니다');
    if (text.length > 300)     return sendError(res, 400, '텍스트는 300자 이하여야 합니다');

    let patient_id;
    try {
        patient_id = await get_patient_id(req.user.mem_id);
        if (!patient_id) return sendError(res, 404, '환자 정보를 찾을 수 없습니다');

        // 기존 음성 삭제
        await delete_patient_voices(patient_id);

        // TTS 생성
        const filename    = `alarm_voice_${patient_id}_${Date.now()}.mp3`;
        const output_abs  = path.join(SOUNDS_DIR, filename);
        await elevenlabs.generate_tts(voice_id, text.trim(), output_abs);

        const relative_sound = `uploads/sounds/${filename}`;

        // voice_samples 저장
        const { rows } = await pool.query(
            `INSERT INTO voice_samples
               (patient_id, file_name, file_path, file_size, mime_type, status)
             VALUES ($1, $2, $3, $4, 'audio/mpeg', 'ready')
             RETURNING voice_id, file_name, status, uploaded_at, updated_at`,
            [
                patient_id,
                filename,
                relative_sound,
                fs.statSync(output_abs).size,
            ]
        );

        return sendSuccess(res, 201, { voice: rows[0] });
    } catch (err) {
        console.error('[POST /api/voice/generate]', err.message);
        return sendError(res, 502, 'TTS 생성에 실패했습니다. 잠시 후 다시 시도해주세요.');
    }
});

// ─── DELETE /api/voice ────────────────────────────────────────────────────────
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
        return sendSuccess(res, 200, { message: '알림 음성이 삭제되었습니다' });
    } catch (err) {
        console.error('[DELETE /api/voice]', err);
        return sendError(res, 500, '서버 오류가 발생했습니다');
    }
});

module.exports = router;
