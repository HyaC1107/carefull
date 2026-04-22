const axios = require('axios');

const max_retries_per_model = 2;

const prompt_text = `
Analyze the prescription image and extract only clearly visible information.

Rules:
- Do not guess.
- If a value is unclear, set it to null.
- If a list value is unclear, return an empty array.
- This is a draft for user review and correction before registration.
- Return JSON only.
- Do not include markdown, code fences, explanations, or extra text.

Target JSON structure:
{
  "patient_name": "string or null",
  "medicines": [
    {
      "name": "string or null",
      "dose": "string or null",
      "frequency_per_day": "number or null",
      "timing": [],
      "duration_days": "number or null",
      "instruction": "string or null",
      "uncertain_fields": []
    }
  ]
}
`.trim();

const create_error = (message, status_code = 500, extra = {}) => {
    const error = new Error(message);
    error.status_code = status_code;

    for (const [key, value] of Object.entries(extra)) {
        error[key] = value;
    }

    return error;
};

const get_candidate_models = () => {
    const model_values = [
        process.env.GEMINI_PRIMARY_MODEL,
        process.env.GEMINI_SECONDARY_MODEL,
        process.env.GEMINI_FALLBACK_MODEL
    ];

    return [...new Set(
        model_values
            .map((value) => (typeof value === 'string' ? value.trim() : ''))
            .filter(Boolean)
    )];
};

const is_retryable_gemini_error = (error) => {
    if (!error) {
        return false;
    }

    if (error.is_network_error) {
        return true;
    }

    return [404, 429, 503].includes(error.status_code);
};

const extract_json_candidate = (text) => {
    const trimmed_text = String(text || '').trim();

    if (!trimmed_text) {
        return '';
    }

    const code_block_match = trimmed_text.match(/```json\s*([\s\S]*?)```/i)
        || trimmed_text.match(/```\s*([\s\S]*?)```/i);

    if (code_block_match && code_block_match[1]) {
        return code_block_match[1].trim();
    }

    const first_object_index = trimmed_text.indexOf('{');
    const last_object_index = trimmed_text.lastIndexOf('}');

    if (first_object_index !== -1 && last_object_index !== -1 && last_object_index > first_object_index) {
        return trimmed_text.slice(first_object_index, last_object_index + 1).trim();
    }

    return trimmed_text;
};

const extract_response_text = (response_data) => {
    const candidates = response_data?.candidates;

    if (!Array.isArray(candidates) || candidates.length === 0) {
        throw create_error('Gemini returned an empty response.', 502, {
            should_fallback: true
        });
    }

    const candidate = candidates[0];
    const parts = candidate?.content?.parts;

    if (!Array.isArray(parts) || parts.length === 0) {
        throw create_error('Gemini returned an invalid response format.', 502, {
            should_fallback: true
        });
    }

    const text = parts
        .map((part) => part?.text)
        .filter((value) => typeof value === 'string')
        .join('')
        .trim();

    if (!text) {
        throw create_error('Gemini returned an empty text response.', 502, {
            should_fallback: true
        });
    }

    return text;
};

const parse_gemini_json = (response_text) => {
    const json_candidate = extract_json_candidate(response_text);

    if (!json_candidate) {
        throw create_error('Gemini JSON content is empty.', 502, {
            should_fallback: true
        });
    }

    try {
        return JSON.parse(json_candidate);
    } catch (error) {
        throw create_error('Failed to parse Gemini JSON response.', 502, {
            should_fallback: true
        });
    }
};

const normalize_string_value = (value) => {
    if (typeof value !== 'string') {
        return '';
    }

    return value.trim();
};

const normalize_nullable_string = (value) => {
    if (typeof value !== 'string') {
        return null;
    }

    const trimmed_value = value.trim();
    return trimmed_value || null;
};

const normalize_nullable_number = (value) => {
    if (value === null || value === undefined || value === '') {
        return null;
    }

    const parsed_value = Number(value);

    if (!Number.isFinite(parsed_value)) {
        return null;
    }

    return parsed_value;
};

const normalize_string_array = (value) => {
    if (!Array.isArray(value)) {
        return [];
    }

    return value
        .filter((item) => typeof item === 'string')
        .map((item) => item.trim())
        .filter(Boolean);
};

const normalize_prescription_draft = (draft) => {
    const medicines = Array.isArray(draft?.medicines) ? draft.medicines : [];

    return {
        patient_name: normalize_nullable_string(draft?.patient_name),
        medicines: medicines.map((medicine, index) => ({
            temp_id: index + 1,
            name: normalize_string_value(medicine?.name),
            dose: normalize_string_value(medicine?.dose),
            frequency_per_day: normalize_nullable_number(medicine?.frequency_per_day),
            timing: normalize_string_array(medicine?.timing),
            duration_days: normalize_nullable_number(medicine?.duration_days),
            instruction: normalize_string_value(medicine?.instruction),
            uncertain_fields: normalize_string_array(medicine?.uncertain_fields)
        }))
    };
};

const call_gemini_generate_content = async (model, file) => {
    const gemini_api_key = process.env.GEMINI_API_KEY;

    if (!gemini_api_key) {
        throw create_error('GEMINI_API_KEY is not configured.', 500);
    }

    const request_url = `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent`;

    try {
        const { data } = await axios.post(
            request_url,
            {
                contents: [
                    {
                        parts: [
                            {
                                text: prompt_text
                            },
                            {
                                inlineData: {
                                    mimeType: file.mimetype,
                                    data: file.buffer.toString('base64')
                                }
                            }
                        ]
                    }
                ],
                generationConfig: {
                    responseMimeType: 'application/json'
                }
            },
            {
                params: {
                    key: gemini_api_key
                },
                headers: {
                    'Content-Type': 'application/json'
                },
                timeout: 30000
            }
        );

        return {
            raw_response: data,
            response_text: extract_response_text(data)
        };
    } catch (error) {
        if (error.status_code) {
            throw error;
        }

        if (error.response) {
            const message =
                error.response.data?.error?.message ||
                `Gemini request failed for model ${model}.`;

            throw create_error(message, error.response.status, {
                model
            });
        }

        throw create_error(`Network error while requesting Gemini model ${model}.`, 502, {
            model,
            is_network_error: true
        });
    }
};

const analyze_prescription_image = async (file) => {
    const candidate_models = get_candidate_models();

    if (candidate_models.length === 0) {
        throw create_error('Gemini model is not configured. Check GEMINI_PRIMARY_MODEL, GEMINI_SECONDARY_MODEL, and GEMINI_FALLBACK_MODEL.', 500);
    }

    let last_error = null;
    const failed_models = [];

    for (const model of candidate_models) {
        for (let retry_count = 0; retry_count <= max_retries_per_model; retry_count += 1) {
            const attempt = retry_count + 1;

            try {
                const { response_text } = await call_gemini_generate_content(model, file);
                const parsed_draft = parse_gemini_json(response_text);

                return normalize_prescription_draft(parsed_draft);
            } catch (error) {
                last_error = error;

                const status_code = error.status_code || 502;
                const should_move_to_next_model = error.should_fallback || retry_count === max_retries_per_model;

                console.error(
                    `Prescription Gemini request failed. model=${model}, attempt=${attempt}, status_code=${status_code}, reason=${error.message}`
                );

                if (!is_retryable_gemini_error(error) && !error.should_fallback) {
                    throw error;
                }

                if (should_move_to_next_model) {
                    failed_models.push({
                        model,
                        attempt,
                        status_code,
                        reason: error.message
                    });
                    break;
                }
            }
        }
    }

    const last_failed_model = failed_models.length > 0
        ? failed_models[failed_models.length - 1]
        : null;

    throw create_error(
        `Failed to analyze prescription image. model=${last_failed_model?.model || last_error?.model || 'unknown'}, status_code=${last_failed_model?.status_code || last_error?.status_code || 500}, reason=${last_failed_model?.reason || last_error?.message || 'Unknown error.'}`,
        last_failed_model?.status_code || last_error?.status_code || 500,
        {
            failed_models
        }
    );
};

module.exports = {
    analyze_prescription_image
};
