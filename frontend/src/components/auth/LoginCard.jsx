// 이 파일이 하는 일
// 가운데 흰색 카드 전체를 담당.
// 여기서 로고, 제목, 설명, 버튼 3개를 모아놓았음.
import SocialLoginButton from './SocialLoginButton'
import '../../styles/LoginCard.css'

function LoginCard({ onKakaoLogin, onNaverLogin, onGoogleLogin }) {
  return (
    <section className="login-card">
      <div className="login-card__logo" aria-hidden="true">
        <img
          src="/yakssok-logo.png"
          alt=""
          className="login-card__logo-image"
        />
      </div>

      <p className="login-card__subtitle">Care-full 스마트 복약 관리 서비스</p>

      <div className="login-card__actions">
        <SocialLoginButton
          provider="kakao"
          label="카카오 로그인"
          className="login-card__button login-card__button--kakao"
          onClick={onKakaoLogin}
        />
        <SocialLoginButton
          provider="naver"
          label="네이버 로그인"
          className="login-card__button login-card__button--naver"
          onClick={onNaverLogin}
        />
        <SocialLoginButton
          provider="google"
          label="구글 로그인"
          className="login-card__button login-card__button--google"
          onClick={onGoogleLogin}
        />
      </div>
    </section>
  )
}

export default LoginCard