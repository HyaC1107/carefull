const jwt = require('jsonwebtoken');

/**
 * Authorization 헤더의 Bearer 토큰을 검증하고,
 * 프로젝트 전역에서 req.user.memberId 형태로 일관되게 접근할 수 있게 정규화합니다.
 *
 * 왜 수정했는가:
 * - 기존 코드는 jwt.verify() 결과 전체를 req.user에 그대로 넣었습니다.
 * - 이 방식은 payload 구조가 바뀌면 req.user 내부 shape도 함께 흔들립니다.
 * - 따라서 인증 후 코드가 믿고 사용할 공통 형태를 여기서 고정합니다.
 */
const verifyToken = (req, res, next) => {
    const authHeader = req.headers.authorization;
    const token = authHeader && authHeader.split(' ')[1];

    if (!token) {
        return res.status(403).json({
            success: false,
            message: '인증 토큰이 없습니다.'
        });
    }

    try {
        const decoded = jwt.verify(token, process.env.JWT_SECRET);

        /**
         * 현재 워크스페이스 기준으로 jwt.sign()에 담기는 사용자 식별자는 memberId입니다.
         * member_id가 담기는 코드는 확인되지 않았습니다.
         */
        if (!decoded.memberId) {
            return res.status(401).json({
                success: false,
                message: '토큰에 memberId가 없습니다.'
            });
        }

        req.user = {
            memberId: decoded.memberId,
            nickname: decoded.nickname,
            iat: decoded.iat,
            exp: decoded.exp
        };

        next();
    } catch (error) {
        return res.status(401).json({
            success: false,
            message: '유효하지 않은 인증 토큰입니다.'
        });
    }
};

module.exports = { verifyToken };
