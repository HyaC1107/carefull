const fs   = require('fs');
const path = require('path');
const { ElevenLabsClient } = require('@elevenlabs/elevenlabs-js');

const MODEL_ID     = 'eleven_v3';
const DEFAULT_TEXT = '약 먹을 시간이에요. 보호자님이 알려드려요. 물과 함께 천천히 약을 복용해주세요.';

function get_client() {
    const api_key = process.env.ELEVENLABS_API_KEY;
    if (!api_key) throw new Error('ELEVENLABS_API_KEY 환경변수가 설정되지 않았습니다');
    return new ElevenLabsClient({ apiKey: api_key });
}

// ── 보이스 목록 캐시 ──────────────────────────────────────────────────────────
let _voices_cache    = null;
let _voices_cache_at = 0;
const VOICES_CACHE_TTL = 30 * 60 * 1000; // 30분

/**
 * ElevenLabs 기성(premade) 목소리 목록 반환
 */
async function get_voices() {
    const now = Date.now();
    if (_voices_cache && now - _voices_cache_at < VOICES_CACHE_TTL) {
        return _voices_cache;
    }

    const client = get_client();
    // getAll() → Promise<GetVoicesResponse> → { voices: Voice[] }
    // Voice.voiceId (camelCase)
    const { voices } = await client.voices.getAll();

    const result = (voices || [])
        .filter(v => v.category === 'premade')
        .map(v => ({
            voice_id: v.voiceId,
            name:     v.name  || '',
            labels:   v.labels || {},
        }));

    _voices_cache    = result;
    _voices_cache_at = now;
    return result;
}

/**
 * 지정된 목소리와 텍스트로 TTS MP3 생성 → output_path에 저장
 * @returns {string} 저장된 파일의 절대 경로
 */
async function generate_tts(voice_id, text, output_path) {
    const client = get_client();

    // convert() → Promise<ReadableStream<Uint8Array>>
    const audio_stream = await client.textToSpeech.convert(voice_id, {
        text,
        modelId:      MODEL_ID,
        outputFormat: 'mp3_44100_128',
        voiceSettings: {
            stability:       0.5,
            similarityBoost: 0.75,
        },
    });

    // Node.js 18+: ReadableStream<Uint8Array> 은 async iterable 지원
    const chunks = [];
    for await (const chunk of audio_stream) {
        chunks.push(Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk));
    }

    fs.mkdirSync(path.dirname(output_path), { recursive: true });
    fs.writeFileSync(output_path, Buffer.concat(chunks));
    return output_path;
}

/**
 * ElevenLabs에서 클로닝 보이스 삭제 (필요 시 사용)
 */
async function delete_voice(voice_id) {
    const client = get_client();
    await client.voices.delete(voice_id);
}

module.exports = { get_voices, generate_tts, delete_voice, DEFAULT_TEXT };
