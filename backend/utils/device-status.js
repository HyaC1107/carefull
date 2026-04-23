const DEVICE_PING_THRESHOLD_MS = 10 * 60 * 1000;

const is_device_online = (last_ping, now = new Date()) => {
    if (!last_ping) {
        return false;
    }

    const last_ping_date = new Date(last_ping);

    if (Number.isNaN(last_ping_date.getTime())) {
        return false;
    }

    return now.getTime() - last_ping_date.getTime() <= DEVICE_PING_THRESHOLD_MS;
};

module.exports = {
    DEVICE_PING_THRESHOLD_MS,
    is_device_online
};
