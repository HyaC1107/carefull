// 이 파일이 하는 일
// 이건 버튼 하나짜리 공통 부품.
// 카카오/네이버/구글 버튼을 각각 따로 3개 만든 게 아니라
// 하나의 버튼 컴포넌트를 만들고 provider 값만 바꿔서 재사용.
function SocialLoginButton({ provider, label, onClick }) {
  const providerMap = {
    kakao: {
      className: 'social-button social-button--kakao',
      icon: 'K',
      iconClass: 'social-button__icon social-button__icon--dark',
    },
    naver: {
      className: 'social-button social-button--naver',
      icon: 'N',
      iconClass: 'social-button__icon social-button__icon--light',
    },
    google: {
      className: 'social-button social-button--google',
      icon: 'G',
      iconClass: 'social-button__icon social-button__icon--google',
    },
  }

  const config = providerMap[provider]

  return (
    <button type="button" className={config.className} onClick={onClick}>
      <span className={config.iconClass} aria-hidden="true">
        {config.icon}
      </span>
      <span className="social-button__label">{label}</span>
    </button>
  )
}

export default SocialLoginButton