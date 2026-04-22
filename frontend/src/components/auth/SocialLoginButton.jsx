// 이 파일이 하는 일
// 이건 버튼 하나짜리 공통 부품.
// 카카오/네이버/구글 버튼을 각각 따로 3개 만든 게 아니라
// 하나의 버튼 컴포넌트를 만들고 provider 값만 바꿔서 재사용.
import { SiKakaotalk, SiNaver } from 'react-icons/si'
import { FcGoogle } from 'react-icons/fc'

function SocialLoginButton({ provider, label, className = '', onClick }) {
  const icon = getProviderIcon(provider)

  return (
    <button
      type="button"
      className={`social-login-button ${className}`}
      onClick={onClick}
    >
      <span className="social-login-button__icon" aria-hidden="true">
        {icon}
      </span>
      <span className="social-login-button__label">{label}</span>
    </button>
  )
}

function getProviderIcon(provider) {
  switch (provider) {
    case 'kakao':
      return <SiKakaotalk size={18} color="#191919" />
    case 'naver':
      return <SiNaver size={16} color="#ffffff" />
    case 'google':
      return <FcGoogle size={18} />
    default:
      return null
  }
}

export default SocialLoginButton