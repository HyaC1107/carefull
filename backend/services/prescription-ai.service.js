const axios = require('axios');

const DATE_PATTERN = /^\d{4}-\d{2}-\d{2}$/;
const TIME_PATTERN = /^([01]\d|2[0-3]):[0-5]\d(:[0-5]\d)?$/;

const get_gemini_candidates = () => [
    process.env.GEMINI_MODEL,
    process.env.GEMINI_FALLBACK_MODEL
].filter(Boolean);

const build_prompt = () => `
You extract medication schedules from one Korean prescription image.
Return JSON only. Do not wrap it in markdown.
Schema:
{
  "medications": [
    {
      "medicine_name": "string",
      "dose": "string",
      "times": ["HH:MM"],
      "start_date": "YYYY-MM-DD",
      "end_date": "YYYY-MM-DD or null",
      "memo": "string"
    }
  ],
  "warnings": ["string"]
}
If a value is unclear, keep the closest safe value and add a Korean warning.
Use today's date only when the prescription has no usable start date.
`;

const normalize_time = (value) => {
    if (!value) return null;

    const trimmed = String(value).trim();
    const match = trimmed.match(/^(\d{1,2}):(\d{2})(?::(\d{2}))?$/);

    if (!match) return null;

    const hours = Number(match[1]);
    const minutes = Number(match[2]);
    const seconds = match[3] === undefined ? 0 : Number(match[3]);

    if (
        !Number.isInteger(hours) ||
        !Number.isInteger(minutes) ||
        !Number.isInteger(seconds) ||
        hours < 0 ||
        hours > 23 ||
        minutes < 0 ||
        minutes > 59 ||
        seconds < 0 ||
        seconds > 59
    ) {
        return null;
    }

    return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}`;
};

const normalize_date = (value) => {
    if (!value) return null;

    const normalized = String(value).slice(0, 10);
    if (!DATE_PATTERN.test(normalized)) return null;

    const date = new Date(`${normalized}T00:00:00`);
    return Number.isNaN(date.getTime()) ? null : normalized;
};

const strip_json_fence = (value) => {
    const text = String(value || '').trim();
    const fenced = text.match(/^```(?:json)?\s*([\s\S]*?)\s*```$/i);

    return fenced ? fenced[1].trim() : text;
};

const extract_text_from_gemini = (response_data) => {
    const parts = response_data?.candidates?.[0]?.content?.parts;
    if (!Array.isArray(parts)) return '';

    return parts.map((part) => part?.text || '').join('').trim();
};

const parse_gemini_json = (text) => {
    const json_text = strip_json_fence(text);
    return JSON.parse(json_text);
};

const normalize_prescription_payload = (payload) => {
    const warnings = Array.isArray(payload?.warnings)
        ? payload.warnings.filter(Boolean).map((warning) => String(warning))
        : [];
    const source_medications = Array.isArray(payload?.medications)
        ? payload.medications
        : [];

    if (source_medications.length === 0) {
        warnings.push('분석된 복약 일정이 없습니다.');
    }

    const medications = source_medications.map((item, index) => {
        const medicine_name = String(item?.medicine_name || item?.medi_name || '').trim();
        const raw_times = Array.isArray(item?.times) ? item.times : [];
        const times = raw_times
            .map(normalize_time)
            .filter(Boolean)
            .filter((time, time_index, list) => list.indexOf(time) === time_index);
        const start_date = normalize_date(item?.start_date);
        const end_date = normalize_date(item?.end_date);
        const dose = String(item?.dose || '').trim();
        const memo = String(item?.memo || item?.note || '').trim();

        if (!medicine_name) {
            warnings.push(`${index + 1}번째 약 이름을 확인해야 합니다.`);
        }

        if (!start_date) {
            warnings.push(`${medicine_name || `${index + 1}번째 약`}의 시작일을 확인해야 합니다.`);
        }

        if (item?.end_date && !end_date) {
            warnings.push(`${medicine_name || `${index + 1}번째 약`}의 종료일 형식이 올바르지 않습니다.`);
        }

        if (raw_times.length === 0 || times.length === 0) {
            warnings.push(`${medicine_name || `${index + 1}번째 약`}의 복용 시간이 없습니다.`);
        }

        if (raw_times.length > 0 && raw_times.length !== times.length) {
            warnings.push(`${medicine_name || `${index + 1}번째 약`}의 복용 시간 일부를 확인해야 합니다.`);
        }

        return {
            medicine_name,
            dose,
            times,
            start_date,
            end_date,
            memo
        };
    });

    return {
        medications,
        warnings: [...new Set(warnings)]
    };
};

const validate_prescription_confirm = (payload) => {
    const normalized = normalize_prescription_payload(payload);
    const errors = [];

    if (normalized.medications.length === 0) {
        errors.push('medications must not be empty.');
    }

    normalized.medications.forEach((item, index) => {
        const label = item.medicine_name || `${index + 1}번째 약`;

        if (!item.medicine_name) {
            errors.push(`${label}: medicine_name is required.`);
        }

        if (!item.start_date) {
            errors.push(`${label}: start_date is required.`);
        }

        if (!Array.isArray(item.times) || item.times.length === 0) {
            errors.push(`${label}: times must not be empty.`);
        }

        item.times.forEach((time) => {
            if (!TIME_PATTERN.test(`${time}:00`)) {
                errors.push(`${label}: invalid time format.`);
            }
        });
    });

    return {
        normalized,
        errors
    };
};

const call_gemini = async ({ image_buffer, mime_type }) => {
    const api_key = process.env.GEMINI_API_KEY;
    const api_url = process.env.GEMINI_API_URL;
    const models = get_gemini_candidates();

    if (!api_key || !api_url || models.length === 0) {
        throw new Error('Gemini environment variables are not configured.');
    }

    let last_error;

    for (const model of models) {
        try {
            const url = new URL(api_url);
            url.pathname = url.pathname.replace(/\/$/, '');
            url.pathname = `${url.pathname}/models/${encodeURIComponent(model)}:generateContent`;
            url.searchParams.set('key', api_key);

            const response = await axios.post(url.toString(), {
                contents: [
                    {
                        role: 'user',
                        parts: [
                            { text: build_prompt() },
                            {
                                inline_data: {
                                    mime_type,
                                    data: image_buffer.toString('base64')
                                }
                            }
                        ]
                    }
                ],
                generationConfig: {
                    responseMimeType: 'application/json'
                }
            });

            return parse_gemini_json(extract_text_from_gemini(response.data));
        } catch (error) {
            last_error = error;
        }
    }

    throw last_error || new Error('Gemini analysis failed.');
};

module.exports = {
    call_gemini,
    normalize_prescription_payload,
    validate_prescription_confirm
};
