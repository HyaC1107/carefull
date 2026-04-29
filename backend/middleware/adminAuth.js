const jwt = require('jsonwebtoken');

const verifyAdminToken = (req, res, next) => {
    const auth_header = req.headers.authorization;
    const token = auth_header && auth_header.split(' ')[1];

    if (!token) {
        return res.status(403).json({ success: false, message: '관리자 인증 토큰이 없습니다.' });
    }

    try {
        const decoded = jwt.verify(token, process.env.JWT_SECRET);

        if (!decoded.admin_id) {
            return res.status(401).json({ success: false, message: '관리자 토큰이 아닙니다.' });
        }

        req.admin = {
            admin_id: decoded.admin_id,
            login_id: decoded.login_id,
            name:     decoded.name,
            role:     decoded.role,
        };

        next();
    } catch {
        return res.status(401).json({ success: false, message: '유효하지 않은 관리자 토큰입니다.' });
    }
};

module.exports = { verifyAdminToken };
