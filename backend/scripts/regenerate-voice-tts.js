const path = require('path');
const dotenv = require('dotenv');

dotenv.config({ path: path.join(__dirname, '..', '.env') });

const pool = require('../db');
const elevenlabs = require('../services/elevenlabs.service');

function print_usage() {
    console.log('Usage: npm run regen:voice-tts -- [--voice-id <voice_id> | --patient-id <patient_id>]');
    console.log('No argument: uses the latest ready voice_samples row with elevenlabs_voice_id.');
}

function get_arg_value(args, name) {
    const index = args.indexOf(name);
    if (index === -1) return null;
    return args[index + 1] || null;
}

function parse_positive_int(value, label) {
    if (value === null || value === undefined) return null;
    const parsed = Number(value);
    if (!Number.isInteger(parsed) || parsed <= 0) {
        throw new Error(`${label} must be a positive integer.`);
    }
    return parsed;
}

async function find_voice_sample({ voice_id, patient_id }) {
    if (voice_id) {
        const { rows } = await pool.query(
            `SELECT voice_id, patient_id, elevenlabs_voice_id
             FROM voice_samples
             WHERE voice_id = $1
             LIMIT 1`,
            [voice_id]
        );
        return rows[0] || null;
    }

    if (patient_id) {
        const { rows } = await pool.query(
            `SELECT voice_id, patient_id, elevenlabs_voice_id
             FROM voice_samples
             WHERE patient_id = $1
               AND status = 'ready'
             ORDER BY updated_at DESC, uploaded_at DESC, voice_id DESC
             LIMIT 1`,
            [patient_id]
        );
        return rows[0] || null;
    }

    const { rows } = await pool.query(
        `SELECT voice_id, patient_id, elevenlabs_voice_id
         FROM voice_samples
         WHERE status = 'ready'
           AND elevenlabs_voice_id IS NOT NULL
         ORDER BY updated_at DESC, uploaded_at DESC, voice_id DESC
         LIMIT 1`
    );
    return rows[0] || null;
}

async function find_device(patient_id) {
    const { rows } = await pool.query(
        `SELECT device_id, device_uid
         FROM devices
         WHERE patient_id = $1
         ORDER BY registered_at DESC, device_id DESC
         LIMIT 1`,
        [patient_id]
    );
    return rows[0] || null;
}

async function main() {
    const args = process.argv.slice(2);

    if (args.includes('--help') || args.includes('-h')) {
        print_usage();
        return;
    }

    const voice_id = parse_positive_int(get_arg_value(args, '--voice-id'), 'voice_id');
    const patient_id = parse_positive_int(get_arg_value(args, '--patient-id'), 'patient_id');

    if (voice_id && patient_id) {
        throw new Error('Use either --voice-id or --patient-id, not both.');
    }

    const sample = await find_voice_sample({ voice_id, patient_id });
    if (!sample) {
        throw new Error('No matching ready voice sample found.');
    }

    if (!sample.elevenlabs_voice_id) {
        throw new Error(`voice_id=${sample.voice_id} has no elevenlabs_voice_id.`);
    }

    const device = await find_device(sample.patient_id);
    if (!device) {
        throw new Error(`No device row found for patient_id=${sample.patient_id}.`);
    }

    const filename = `alarm_voice_${sample.voice_id}_${Date.now()}.mp3`;
    const output_abs = path.join(__dirname, '..', 'uploads', 'sounds', filename);
    const relative_sound = path.join('uploads', 'sounds', filename).replace(/\\/g, '/');

    await elevenlabs.text_to_speech(sample.elevenlabs_voice_id, output_abs);

    await pool.query(
        `UPDATE devices
         SET alarm_sound_path = $1,
             alarm_sound_name = $2,
             alarm_sound_updated_at = NOW()
         WHERE device_id = $3`,
        [relative_sound, filename, device.device_id]
    );

    console.log(`REGEN_VOICE_TTS_SUCCESS voice_id=${sample.voice_id} patient_id=${sample.patient_id}`);
    console.log(`file_path=${relative_sound}`);
    console.log(`file_name=${filename}`);
    console.log(`device_uid=${device.device_uid}`);
}

main()
    .catch((error) => {
        console.error(`REGEN_VOICE_TTS_ERROR message=${error.message}`);
        process.exitCode = 1;
    })
    .finally(async () => {
        await pool.end().catch(() => {});
    });
