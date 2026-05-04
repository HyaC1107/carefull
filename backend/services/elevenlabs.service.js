const fs   = require('fs');
const path = require('path');
const axios = require('axios');

const BASE_URL      = 'https://api.elevenlabs.io/v1';
const FIXED_MESSAGE = '약 먹을 시간이에요. 보호자님이 알려드려요. 물과 함께 천천히 약을 복용해주세요.';
const MODEL_ID      = 'eleven_multilingual_v2';

function api_key() {
    const key = process.env.ELEVENLABS_API_KEY;
    if (!key) throw new Error('ELEVENLABS_API_KEY 환경변수가 설정되지 않았습니다');
    return key;
}

/**
 * 오디오 파일로 ElevenLabs 보이스 클로닝
 * @returns {string} elevenlabs voice_id
 */
async function clone_voice(audio_file_path, voice_name) {
    const key = process.env.ELEVENLABS_API_KEY;
    if (!key) throw new Error('ELEVENLABS_API_KEY is not configured');

    const buffer = fs.readFileSync(audio_file_path);
    const ext    = path.extname(audio_file_path).slice(1).toLowerCase() || 'webm';
    const mime   = ext === 'mp3' ? 'audio/mpeg' : `audio/${ext}`;

    const form = new FormData();
    form.append('name', voice_name);
    form.append('files', new Blob([buffer], { type: mime }), path.basename(audio_file_path));

    let data;
    try {
        ({ data } = await axios.post(`${BASE_URL}/voices/add`, form, {
            headers: { 'xi-api-key': key },
            timeout: 60_000,
        }));
    } catch (err) {
        const response_message = err.response?.data?.detail || err.response?.data?.message || err.message;
        const message_text = typeof response_message === 'string'
            ? response_message
            : JSON.stringify(response_message);
        if (message_text.includes('paid_plan_required') || message_text.includes('can_not_use_instant_voice_cloning')) {
            err.message = `ElevenLabs paid_plan_required: ${message_text}`;
        }
        console.error('[ElevenLabs] clone_voice failed:', {
            status: err.response?.status,
            message: message_text,
        });
        throw err;
    }

    if (!data.voice_id) throw new Error('ElevenLabs 응답에 voice_id가 없습니다');
    return data.voice_id;
}

/**
 * 고정 메시지를 클로닝된 목소리로 TTS 생성 → 파일로 저장
 * @returns {string} 저장된 파일의 절대 경로
 */
async function text_to_speech(voice_id, output_path) {
    const key = process.env.ELEVENLABS_API_KEY;
    if (!key) throw new Error('ELEVENLABS_API_KEY is not configured');

    let response;
    try {
        response = await axios.post(
            `${BASE_URL}/text-to-speech/${voice_id}`,
            {
                text: FIXED_MESSAGE,
                model_id: process.env.ELEVENLABS_MODEL_ID || MODEL_ID || 'eleven_multilingual_v2',
                voice_settings: { stability: 0.5, similarity_boost: 0.75 },
            },
            {
                headers: {
                    'xi-api-key': key,
                    'Content-Type': 'application/json',
                    'Accept': 'audio/mpeg',
                },
                params: { output_format: 'mp3_44100_128' },
                responseType: 'arraybuffer',
                timeout: 60_000,
            }
        );
    } catch (err) {
        console.error('[ElevenLabs] text_to_speech failed:', {
            status: err.response?.status,
            message: err.response?.data?.detail || err.response?.data?.message || err.message,
        });
        throw err;
    }

    fs.mkdirSync(path.dirname(output_path), { recursive: true });
    fs.writeFileSync(output_path, Buffer.from(response.data));
    return output_path;
}

/**
 * ElevenLabs에서 보이스 삭제
 */
async function delete_voice(voice_id) {
    await axios.delete(`${BASE_URL}/voices/${voice_id}`, {
        headers: { 'xi-api-key': api_key() },
        timeout: 15_000,
    });
}

module.exports = { clone_voice, text_to_speech, delete_voice, FIXED_MESSAGE };
