const { ACTIVITY_STATUS } = require('./activity-status');

/**
 * 완료로 인정할 로그 상태 목록입니다.
 */
const COMPLETED_STATUSES = [ACTIVITY_STATUS.SUCCESS, 'COMPLETED', 'TAKEN'];

/**
 * 미복약 또는 실패로 인정할 로그 상태 목록입니다.
 */
const MISSED_STATUSES = [
    ACTIVITY_STATUS.MISSED,
    ACTIVITY_STATUS.FAILED,
    ACTIVITY_STATUS.ERROR
];

/**
 * 마지막 동기화 시간이 10분 이상 차이나면 경고로 봅니다.
 */
const TEN_MINUTES_IN_MS = 10 * 60 * 1000;

/**
 * 약통 잔량이 30 이하이면 부족 경고로 봅니다.
 */
const LOW_MEDICATION_THRESHOLD = 30;
const KST_TIME_ZONE = 'Asia/Seoul';

const getKstDateString = (date = new Date()) => (
    new Date(date).toLocaleString('sv-SE', {
        timeZone: KST_TIME_ZONE,
        year: 'numeric',
        month: '2-digit',
        day: '2-digit'
    }).slice(0, 10)
);

const getKstWallClockDate = (date = new Date()) => (
    new Date(new Date(date).toLocaleString('en-US', { timeZone: KST_TIME_ZONE }))
);

const buildKstDateTimeString = (date, timeValue) => {
    const date_string = getKstDateString(date);
    const [hours = '00', minutes = '00', seconds = '00'] = String(timeValue || '')
        .split(':');

    return `${date_string}T${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(seconds || '00').padStart(2, '0')}+09:00`;
};

/**
 * 오늘 날짜를 YYYY-MM-DD 문자열로 반환합니다.
 * 예: 2026-04-15
 */
const getTodayDateString = () => {
    return getKstDateString();
};
/**
 * JavaScript 요일(일요일 0 ~ 토요일 6)을
 * 프로젝트에서 사용하는 요일(월요일 1 ~ 일요일 7) 기준으로 변환합니다.
 */
const getProjectDayOfWeek = (date) => {
    const day = date.getDay();
    return day === 0 ? 7 : day;
};

/**
 * 오늘 복약 성공률에 따라 요약 카드의 색상과 메시지를 계산합니다.
 */
const getSummaryStatus = (rate) => {
    if (rate >= 80) {
        return {
            color: 'green',
            message: '양호'
        };
    }

    if (rate >= 50) {
        return {
            color: 'orange',
            message: '주의'
        };
    }

    return {
        color: 'red',
        message: '위험'
    };
};

/**
 * TIME 값과 기준 날짜를 합쳐 Date 객체를 만듭니다.
 *
 * 예:
 * - scheduled_time = '08:30:00'
 * - baseDate = 오늘 날짜
 * - 결과 = 오늘 08:30:00
 */
const buildScheduleTimestamp = (timeValue, baseDate) => {
    if (!timeValue) {
        return null;
    }

    const [hours = 0, minutes = 0, seconds = 0] = String(timeValue)
        .split(':')
        .map(Number);

    const target = new Date(baseDate);
    target.setHours(hours, minutes, seconds || 0, 0);

    return target;
};

/**
 * 일정 상태에 맞는 색상을 반환합니다.
 */
const getScheduleStatusColor = (status) => {
    if (status === '완료') return 'green';
    if (status === '미복약') return 'red';
    if (status === 'Completed') return 'green';
    if (status === 'Missed') return 'red';
    return 'gray';
};

module.exports = {
    COMPLETED_STATUSES,
    MISSED_STATUSES,
    TEN_MINUTES_IN_MS,
    LOW_MEDICATION_THRESHOLD,
    KST_TIME_ZONE,
    getKstDateString,
    getKstWallClockDate,
    buildKstDateTimeString,
    getTodayDateString,
    getProjectDayOfWeek,
    getSummaryStatus,
    buildScheduleTimestamp,
    getScheduleStatusColor
};
