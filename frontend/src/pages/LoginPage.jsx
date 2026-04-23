import LoginCard from '../components/auth/LoginCard'
import '../styles/LoginPage.css'

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || 'https://192.168.219.225.nip.io'

const SOCIAL_LOGIN_START_PATHS = {
  kakao: '/api/user/kakao',
  google: '/api/user/google',
  naver: '/api/user/naver',
}

function LoginPage() {
  const handleKakaoLogin = () => {
    startSocialLogin('kakao')
  }

  const handleNaverLogin = () => {
    startSocialLogin('naver')
  }

  const handleGoogleLogin = () => {
    startSocialLogin('google')
  }

  return (
    <main className="login-page">
      <LoginCard
        onKakaoLogin={handleKakaoLogin}
        onNaverLogin={handleNaverLogin}
        onGoogleLogin={handleGoogleLogin}
      />
    </main>
  )
}

function startSocialLogin(provider) {
  const loginUrl = buildSocialLoginStartUrl(provider)

  if (!loginUrl) {
    console.error(`unsupported provider: ${provider}`)
    return
  }

  window.location.assign(loginUrl)
}

function buildSocialLoginStartUrl(provider) {
  const path = SOCIAL_LOGIN_START_PATHS[provider]

  if (!path) {
    return ''
  }

  return new URL(path, API_BASE_URL).toString()
}

export default LoginPage
