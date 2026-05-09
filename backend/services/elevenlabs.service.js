const fs   = require('fs');
const path = require('path');
const axios = require('axios');
const { ElevenLabsClient } = require('@elevenlabs/elevenlabs-js');

const MODEL_ID     = 'eleven_multilingual_v2';
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
 * ElevenLabs 보이스 라이브러리에서 한국어 특화(language=ko) 목소리 목록 반환
 */
async function get_voices() {
    const now = Date.now();
    if (_voices_cache && now - _voices_cache_at < VOICES_CACHE_TTL) {
        return _voices_cache;
    }

    const api_key = process.env.ELEVENLABS_API_KEY;
    if (!api_key) {
        console.error('[ELEVENLABS] API Key is missing in process.env');
        throw new Error('ELEVENLABS_API_KEY 환경변수가 설정되지 않았습니다');
    }

    try {
        console.log('[ELEVENLABS] Fetching shared voices... (Key check: OK)');

        // SDK 대신 axios를 사용하여 직접 호출
        const response = await axios.get('https://api.elevenlabs.io/v1/shared-voices', {
            params: {
                language: 'ko',
                page_size: 10
            },
            headers: {
                'xi-api-key': api_key
            }
        });

        const voices = response.data.voices || [];
        console.log(`[ELEVENLABS] Successfully fetched ${voices.length} voices`);

        const result = voices.map(v => ({
            voice_id: v.voice_id,
            name:     v.name  || '',
            labels:   { 
                accent: v.accent || '',
                gender: v.gender || '',
                age: v.age || '',
                use_case: v.use_case || '',
                descriptive: v.descriptive || ''
            },
            preview_url_official: v.preview_url
        }));

        _voices_cache    = result;
        _voices_cache_at = now;
        return result;
    } catch (err) {
        console.error('[ELEVENLABS] API Request Failed:');
        if (err.response) {
            console.error(`  - Status: ${err.response.status}`);
            console.error(`  - Data: ${JSON.stringify(err.response.data)}`);
        } else {
            console.error(`  - Message: ${err.message}`);
        }
        throw err;
    }
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
            speed:           0.90,
        },
    });

    fs.mkdirSync(path.dirname(output_path), { recursive: true });

    // 안정적인 스트리밍 방식으로 파일 쓰기
    const file_stream = fs.createWriteStream(output_path);
    
    try {
        for await (const chunk of audio_stream) {
            file_stream.write(Buffer.from(chunk));
        }
    } catch (err) {
        file_stream.end();
        throw err;
    }

    return new Promise((resolve, reject) => {
        file_stream.end();
        file_stream.on('finish', () => {
            console.log(`[TTS] File saved successfully: ${output_path} (Size: ${fs.statSync(output_path).size} bytes)`);
            resolve(output_path);
        });
        file_stream.on('error', reject);
    });
}

/**
 * ElevenLabs에서 클로닝 보이스 삭제 (필요 시 사용)
 */
async function delete_voice(voice_id) {
    const client = get_client();
    await client.voices.delete(voice_id);
}

module.exports = { get_voices, generate_tts, delete_voice, DEFAULT_TEXT };
