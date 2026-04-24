const ACTIVITY_STATUS = {
    SUCCESS: 'SUCCESS',
    FAILED: 'FAILED',
    MISSED: 'MISSED',
    ERROR: 'ERROR'
};

const DEVICE_EVENT_ACTIVITY_STATUSES = [
    ACTIVITY_STATUS.SUCCESS,
    ACTIVITY_STATUS.FAILED,
    ACTIVITY_STATUS.ERROR
];

// 라즈베리파이 1차 판단 결과를 서버의 공식 상태로 통일한다.
const decideMedicationStatus = ({
    face_verified,
    dispensed,
    action_verified,
    error_code,
    status
}) => {
    if (error_code) {
        return ACTIVITY_STATUS.ERROR;
    }

    if (face_verified && dispensed && action_verified) {
        return ACTIVITY_STATUS.SUCCESS;
    }

    if (status) {
        const normalized_status = String(status).trim().toUpperCase();

        if (DEVICE_EVENT_ACTIVITY_STATUSES.includes(normalized_status)) {
            return normalized_status;
        }
    }

    return ACTIVITY_STATUS.FAILED;
};

module.exports = {
    ACTIVITY_STATUS,
    DEVICE_EVENT_ACTIVITY_STATUSES,
    decideMedicationStatus
};
