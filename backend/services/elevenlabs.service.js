const fs   = require('fs');
const path = require('path');
const axios = require('axios');

const BASE_URL      = 'https://api.elevenlabs.io/v1';
const DEFAULT_TEXT  = '약 먹을 시간이에요. 보호자님이 알려드려요. 물과 함께 천천히 약을 복용해주세요.';
const MODEL_ID      = 'eleven_multilingual_v2';

function api_key() {
    const key = process.env.ELEVENLABS_API_KEY;
    if (!key) throw new Error('ELEVENLABS_API_KEY 환경변수가 설정되지 않았습니다');
    return key;
}

// ── 보이스 목록 캐시 ──────────────────────────────────────────────────────────
let _voices_cache     = null;
let _voices_cache_at  = 0;
const VOICES_CACHE_TTL = 30 * 60 * 1000; // 30분

/**
 * ElevenLabs 기성(premade) 목소리 목록 반환
 */
async function get_voices() {
    const now = Date.now();
    if (_voices_cache && now - _voices_cache_at < VOICES_CACHE_TTL) {
        return _voices_cache;
    }

    const { data } = await axios.get(`${BASE_URL}/voices`, {
        headers: { 'xi-api-key': api_key() },
        timeout: 15_000,
    });

    const voices = (data.voices || [])
        .filter(v => v.category === 'premade')
        .map(v => ({
            voice_id: v.voice_id,
            name:     v.name,
            labels:   v.labels || {},
        }));

    _voices_cache    = voices;
    _voices_cache_at = now;
    return voices;
}

/**
 * 지정된 목소리와 텍스트로 TTS MP3 생성 → output_path에 저장
 * @returns {string} 저장된 파일의 절대 경로
 */
async function generate_tts(voice_id, text, output_path) {
    const response = await axios.post(
        `${BASE_URL}/text-to-speech/${voice_id}`,
        {
            text,
            model_id: process.env.ELEVENLABS_MODEL_ID || MODEL_ID,
            voice_settings: { stability: 0.5, similarity_boost: 0.75 },
        },
        {
            headers: {
                'xi-api-key':   api_key(),
                'Content-Type': 'application/json',
                'Accept':       'audio/mpeg',
            },
            params:       { output_format: 'mp3_44100_128' },
            responseType: 'arraybuffer',
            timeout:       60_000,
        }
    );

    fs.mkdirSync(path.dirname(output_path), { recursive: true });
    fs.writeFileSync(output_path, Buffer.from(response.data));
    return output_path;
}

/**
 * ElevenLabs에서 보이스 삭제 (클로닝된 보이스용, 신규 플로우에서는 미사용)
 */
async function delete_voice(voice_id) {
    await axios.delete(`${BASE_URL}/voices/${voice_id}`, {
        headers: { 'xi-api-key': api_key() },
        timeout: 15_000,
    });
}

module.exports = { get_voices, generate_tts, delete_voice, DEFAULT_TEXT };
