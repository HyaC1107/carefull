const sendSuccess = (res, status_code, payload = {}) => {
    return res.status(status_code).json({
        success: true,
        ...payload
    });
};

const sendError = (res, status_code, message, extra = {}) => {
    return res.status(status_code).json({
        success: false,
        message,
        ...extra
    });
};

module.exports = {
    sendSuccess,
    sendError
};
