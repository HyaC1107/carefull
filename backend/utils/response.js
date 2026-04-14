/**
 * 성공 응답 공통 헬퍼입니다.
 * 기존 프론트 연동이 깨지지 않도록 message, patient, schedule 같은
 * 도메인별 키를 그대로 추가로 붙일 수 있게 단순한 형태로 유지합니다.
 */
const sendSuccess = (res, statusCode, payload = {}) => {
    return res.status(statusCode).json({
        success: true,
        ...payload
    });
};

/**
 * 실패 응답 공통 헬퍼입니다.
 * 기존 응답 의미를 유지하기 위해 success / message 중심으로 구성합니다.
 */
const sendError = (res, statusCode, message, extra = {}) => {
    return res.status(statusCode).json({
        success: false,
        message,
        ...extra
    });
};

module.exports = {
    sendSuccess,
    sendError
};
