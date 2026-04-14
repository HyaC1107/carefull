// 이 파일이 하는 일
// 가운데 흰색 카드 전체를 담당.
// 여기서 로고, 제목, 설명, 버튼 3개를 모아놓았음.
import SocialLoginButton from './SocialLoginButton'
import '../../styles/LoginCard.css'

function LoginCard({ onKakaoLogin, onNaverLogin, onGoogleLogin }) {
  return (
    <section className="login-card">
      <div className="login-card__logo" aria-hidden="true">
        <svg
          viewBox="0 0 24 24"
          width="22"
          height="22"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M10 13a4 4 0 0 1 0-6l1.2-1.2a4 4 0 0 1 5.6 5.6L15.5 12" />
          <path d="M14 11a4 4 0 0 1 0 6l-1.2 1.2a4 4 0 0 1-5.6-5.6L8.5 12" />
        </svg>
      </div>

      <h1 className="login-card__title">스마트 복약</h1>
      <p className="login-card__subtitle">복약을 쉽고 편하게 관리하세요</p>

      <div className="login-card__actions">
        <SocialLoginButton
          provider="kakao"
          label="카카오 로그인"
          onClick={onKakaoLogin}
        />
        <SocialLoginButton
          provider="naver"
          label="네이버 로그인"
          onClick={onNaverLogin}
        />
        <SocialLoginButton
          provider="google"
          label="구글 로그인"
          onClick={onGoogleLogin}
        />
      </div>
    </section>
  )
}

export default LoginCard