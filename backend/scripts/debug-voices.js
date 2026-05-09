const axios = require('axios');
const dotenv = require('dotenv');
const path = require('path');

dotenv.config({ path: path.join(__dirname, '..', '.env') });

async function test_voices() {
    const api_key = process.env.ELEVENLABS_API_KEY;
    console.log('API Key exists:', !!api_key);
    if (!api_key) return;

    try {
        console.log('Fetching shared voices...');
        const response = await axios.get('https://api.elevenlabs.io/v1/shared-voices', {
            params: {
                language: 'ko',
                page_size: 10
            },
            headers: {
                'xi-api-key': api_key
            }
        });
        console.log('Success! Found voices:', response.data.voices?.length);
        if (response.data.voices && response.data.voices.length > 0) {
            console.log('First voice sample:', JSON.stringify(response.data.voices[0], null, 2));
        }
    } catch (err) {
        console.error('Error fetching voices:');
        if (err.response) {
            console.error('Status:', err.response.status);
            console.error('Data:', JSON.stringify(err.response.data, null, 2));
        } else {
            console.error('Message:', err.message);
        }
    }
}

test_voices();
