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

// ── 고정된 목소리 목록 (사용자 지정 10인) ───────────────────────────────────────
const FIXED_VOICES = [
    // 여성 (5명)
    { id: 'NHupUXHdYJdFC2k3Gmja', name: '결 (Gyeol)', gender: 'female', age: 'middle_aged' },
    { id: '1BZBO072RKJTzZcDjRox', name: '소라 (Sora)',  gender: 'female', age: 'young' },
    { id: '5n5gqmaQi9Ewevrz7bOS', name: '시안 (Sian)',  gender: 'female', age: 'young' },
    { id: 'NaQdbkW5gNZD8wfwXeTV', name: '온유 (Onyu)',  gender: 'female', age: 'young' },
    { id: '74i8I1pZi98ZjmmYLdaF', name: '클로이 (Chloe)', gender: 'female', age: 'young' },
    // 남성 (5명)
    { id: 'srhGhMYcxqeTNVuSRvWg', name: '준호 (Junho)',  gender: 'male',   age: 'young' },
    { id: 'LKOcTG4J4tYTPR9DnLeM', name: '미스터 K (Mr.K)', gender: 'male',   age: 'young' },
    { id: 'KFTSy1J20kTAnUHnQjVx', name: '재욱 (Jaeuk)',  gender: 'male',   age: 'middle_aged' },
    { id: 'QAuCXfOpYxbxOasYze98', name: '세인 (Sein)',   gender: 'male',   age: 'young' },
    { id: 'mVMNSRhuCVCkUj7v7Eyq', name: '영석 (YoungSeok)', gender: 'male',  age: 'middle_aged' }
];

/**
 * 사용자님이 지정한 고정된 10개의 한국어 목소리 목록 반환
 */
async function get_voices() {
    // 캐시가 유효하면 즉시 반환
    if (_voices_cache && (Date.now() - _voices_cache_at < VOICES_CACHE_TTL)) {
        return _voices_cache;
    }

    console.log('[ELEVENLABS] Returning fixed voice selection (10 voices)');

    const result = FIXED_VOICES.map(v => ({
        voice_id: v.id,
        name:     v.name,
        labels:   { 
            gender: v.gender,
            age:    v.age,
            accent: 'seoul',
            use_case: 'care-service'
        },
        // 고정 ID 방식이므로 공식 미리보기는 null로 처리 (로컬 샘플 우선 사용)
        preview_url_official: null
    }));

    _voices_cache    = result;
    _voices_cache_at = Date.now();
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
