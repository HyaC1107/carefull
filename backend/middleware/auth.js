const jwt = require('jsonwebtoken');

const verifyToken = (req, res, next) => {
    const auth_header = req.headers.authorization;
    const token = auth_header && auth_header.split(' ')[1];

    if (!token) {
        return res.status(403).json({
            success: false,
            message: 'Authentication token is missing.'
        });
    }

    try {
        const decoded = jwt.verify(token, process.env.JWT_SECRET);

        if (!decoded.mem_id) {
            return res.status(401).json({
                success: false,
                message: 'Token does not contain mem_id.'
            });
        }

        req.user = {
            mem_id: decoded.mem_id,
            nick: decoded.nick,
            iat: decoded.iat,
            exp: decoded.exp
        };

        next();
    } catch (error) {
        return res.status(401).json({
            success: false,
            message: 'Invalid authentication token.'
        });
    }
};

module.exports = { verifyToken };
