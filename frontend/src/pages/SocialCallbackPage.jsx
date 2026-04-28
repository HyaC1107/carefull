import { useEffect } from 'react'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { TOKEN_STORAGE_KEY } from '../api'
import '../styles/LoginPage.css'

function SocialCallbackPage() {
  const navigate = useNavigate()
  const { provider } = useParams()
  const [searchParams] = useSearchParams()

  useEffect(() => {
    const runSocialCallback = async () => {
      const normalizedProvider = normalizeProvider(provider)
      const token = searchParams.get('token')
      const providerFromQuery = searchParams.get('provider')
      const error = searchParams.get('error')
      const is_new_user = searchParams.get('is_new_user')

      if (!normalizedProvider || providerFromQuery !== normalizedProvider) {
        navigate('/login', { replace: true })
        return
      }

      if (error || !token) {
        window.alert(error || '로그인 처리 중 오류가 발생했습니다.')
        navigate('/login', { replace: true })
        return
      }

      localStorage.setItem(TOKEN_STORAGE_KEY, token)

      navigate(
        resolveNextPath({
          is_new_user: is_new_user === 'true',
        }),
        { replace: true },
      )
    }

    runSocialCallback()
  }, [navigate, provider, searchParams])

  return <main className="login-page" />
}

function normalizeProvider(provider) {
  if (provider === 'kakao' || provider === 'google' || provider === 'naver') {
    return provider
  }

  return ''
}
function resolveNextPath(authResult) {
  if (authResult.is_new_user || authResult.next_step === '/register-patient') {
    return '/register-patient'
  }

  if (authResult.next_step === '/main' || authResult.next_step === '/dashboard') {
    return '/dashboard'
  }

  return '/dashboard'
}

export default SocialCallbackPage
