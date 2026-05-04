import LoginCard from '../components/auth/LoginCard'
import { API_BASE_URL } from '../api'
import '../styles/LoginPage.css'

const SOCIAL_LOGIN_START_PATHS = {
  kakao: '/api/user/kakao',
  google: '/api/user/google',
  naver: '/api/user/naver',
}

function LoginPage() {
  const handleKakaoLogin = () => startSocialLogin('kakao')
  const handleNaverLogin = () => startSocialLogin('naver')
  const handleGoogleLogin = () => startSocialLogin('google')

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
    console.error(`social login start URL could not be created: ${provider}`)
    return
  }

  window.location.assign(loginUrl)
}

function buildSocialLoginStartUrl(provider) {
  const path = SOCIAL_LOGIN_START_PATHS[provider]
  if (!path) return ''
  if (!API_BASE_URL) {
    console.error('VITE_API_BASE_URL is not configured. Social login cannot start.')
    return ''
  }
  return new URL(path, API_BASE_URL).toString()
}

export default LoginPage
