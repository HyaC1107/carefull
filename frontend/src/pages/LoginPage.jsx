// 이 파일이 하는 일
// 로그인 페이지 전체를 담당.
// 가운데 배경 위에 LoginCard를 올려줌.
// 지금은 테스트용으로 소셜 로그인 버튼을 누르면 대시보드로 이동하게 설정함.
import { useNavigate } from 'react-router-dom'
import LoginCard from '../components/auth/LoginCard'
import '../styles/LoginPage.css'

function LoginPage() {
  // navigate는 코드로 페이지를 이동시킬 때 사용
  const navigate = useNavigate()

  // 지금은 테스트용 이동
  // 나중에 실제 로그인 API 성공 후 navigate('/dashboard')로 바꾸면 됨
  const handleKakaoLogin = () => {
    console.log('카카오 로그인 시작')
    navigate('/dashboard')
  }

  const handleNaverLogin = () => {
    console.log('네이버 로그인 시작')
    navigate('/dashboard')
  }

  const handleGoogleLogin = () => {
    console.log('구글 로그인 시작')
    navigate('/dashboard')
  }

  return (
    <main className="login-page">
      {/* 각 버튼 클릭 시 어떤 함수를 실행할지 LoginCard에 전달 */}
      <LoginCard
        onKakaoLogin={handleKakaoLogin}
        onNaverLogin={handleNaverLogin}
        onGoogleLogin={handleGoogleLogin}
      />
    </main>
  )
}

export default LoginPage