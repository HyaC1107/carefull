const fs = require('fs');
const path = require('path');
const dotenv = require('dotenv');
const { ElevenLabsClient } = require('@elevenlabs/elevenlabs-js');

dotenv.config({ path: path.join(__dirname, '..', '.env') });

function print_usage() {
    console.log('Usage: node scripts/test-elevenlabs-ivc.js <audio-file-path> [--delete]');
}

function normalize_error_message(error) {
    const body = error?.body || error?.response?.data;
    const detail = body?.detail || body?.message || body?.error;
    if (typeof detail === 'string') return detail;
    if (detail) return JSON.stringify(detail);
    return error?.message || 'Unknown error';
}

function classify_error(message) {
    if (message.includes('paid_plan_required') || message.includes('can_not_use_instant_voice_cloning')) {
        return 'PLAN_PERMISSION_REQUIRED';
    }
    if (message.includes('invalid_api_key') || message.includes('Invalid API key')) {
        return 'INVALID_API_KEY';
    }
    return 'IVC_TEST_FAILED';
}

async function main() {
    const args = process.argv.slice(2);
    const should_delete = args.includes('--delete');
    const audio_arg = args.find((arg) => arg !== '--delete');

    if (!audio_arg) {
        print_usage();
        return;
    }

    const audio_path = path.resolve(process.cwd(), audio_arg);
    if (!fs.existsSync(audio_path)) {
        console.error(`FILE_ERROR path_not_found=${audio_arg}`);
        process.exitCode = 1;
        return;
    }

    const api_key = process.env.ELEVENLABS_API_KEY;
    if (!api_key) {
        console.error('CONFIG_ERROR ELEVENLABS_API_KEY is not configured');
        process.exitCode = 1;
        return;
    }

    const client = new ElevenLabsClient({ apiKey: api_key });
    const name = `carefull_ivc_test_${Date.now()}`;
    let voice_id = null;

    try {
        const result = await client.voices.ivc.create({
            name,
            files: [fs.createReadStream(audio_path)],
        });
        voice_id = result.voiceId;
        console.log(`IVC_TEST_SUCCESS voice_id=${voice_id}`);

        if (should_delete && voice_id) {
            await client.voices.delete(voice_id);
            console.log(`IVC_TEST_DELETE_SUCCESS voice_id=${voice_id}`);
        }
    } catch (error) {
        const status = error?.statusCode || error?.status || error?.response?.status || 'unknown';
        const message = normalize_error_message(error);
        const code = classify_error(message);
        console.error(`IVC_TEST_ERROR status=${status} code=${code} message=${message}`);
        if (code === 'PLAN_PERMISSION_REQUIRED') {
            console.error('IVC_TEST_PLAN_PERMISSION_REQUIRED Starter 이상 플랜 또는 IVC 권한이 필요합니다');
        }
        process.exitCode = 1;
    }
}

main();
