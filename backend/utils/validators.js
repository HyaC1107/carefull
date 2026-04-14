/**
 * 숫자 컬럼에 들어갈 값을 안전하게 숫자로 변환합니다.
 * 숫자로 바꿀 수 없으면 null을 반환합니다.
 */
const parseNumericValue = (value) => {
    const parsed = Number(value);
    return Number.isNaN(parsed) ? null : parsed;
};

/**
 * 필수 필드 검증 공통 함수입니다.
 * 문자열은 빈 문자열을 허용하지 않고,
 * 숫자처럼 0이 들어올 수 있는 값은 undefined / null 기준으로만 검사합니다.
 */
const validateRequiredFields = (body, requiredFields) => {
    for (const field of requiredFields) {
        const value = body[field];

        if (typeof value === 'string') {
            if (!value.trim()) {
                return `${field}는 필수입니다.`;
            }
            continue;
        }

        if (value === undefined || value === null) {
            return `${field}는 필수입니다.`;
        }
    }

    return null;
};

/**
 * 지정한 필드들이 숫자인지 한 번에 확인합니다.
 * 숫자가 아닌 필드가 하나라도 있으면 null을 반환합니다.
 */
const parseNumericFields = (body, fields) => {
    const parsed = {};

    for (const field of fields) {
        const value = parseNumericValue(body[field]);
        if (value === null) {
            return null;
        }
        parsed[field] = value;
    }

    return parsed;
};

module.exports = {
    parseNumericValue,
    validateRequiredFields,
    parseNumericFields
};
