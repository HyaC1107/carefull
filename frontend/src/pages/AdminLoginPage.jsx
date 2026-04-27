import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { adminRequest, setAdminToken } from '../adminApi'

export default function AdminLoginPage() {
  const navigate = useNavigate()
  const [loginId, setLoginId]   = useState('')
  const [password, setPassword] = useState('')
  const [error, setError]       = useState('')
  const [loading, setLoading]   = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      const data = await adminRequest('/api/admin/login', {
        method: 'POST',
        body: { login_id: loginId, password },
      })
      setAdminToken(data.token)
      navigate('/admin/dashboard', { replace: true })
    } catch (err) {
      setError(err.message || '로그인에 실패했습니다.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={s.page}>
      <div style={s.card}>
        {/* 로고 영역 */}
        <div style={s.logoWrap}>
          <div style={s.logoIcon}>C</div>
          <span style={s.logoText}>Carefull</span>
        </div>

        <h1 style={s.title}>관리자 로그인</h1>
        <p style={s.sub}>관리자 전용 페이지입니다</p>

        <form onSubmit={handleSubmit} style={s.form}>
          <div style={s.field}>
            <label style={s.label}>아이디</label>
            <input
              style={s.input}
              type="text"
              value={loginId}
              onChange={e => setLoginId(e.target.value)}
              placeholder="관리자 아이디를 입력하세요"
              autoComplete="username"
              autoFocus
              required
            />
          </div>

          <div style={s.field}>
            <label style={s.label}>비밀번호</label>
            <input
              style={s.input}
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              placeholder="비밀번호를 입력하세요"
              autoComplete="current-password"
              required
            />
          </div>

          {error && <p style={s.error}>{error}</p>}

          <button style={{ ...s.btn, opacity: loading ? 0.7 : 1 }} type="submit" disabled={loading}>
            {loading ? '로그인 중...' : '로그인'}
          </button>
        </form>

        <p style={s.backLink} onClick={() => navigate('/login')}>
          ← 일반 로그인으로 돌아가기
        </p>
      </div>
    </div>
  )
}

const s = {
  page: {
    minHeight: '100vh',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    background: 'linear-gradient(135deg, #1e293b 0%, #0f172a 100%)',
  },
  card: {
    width: '100%',
    maxWidth: 420,
    background: '#fff',
    borderRadius: 20,
    padding: '44px 40px 36px',
    boxShadow: '0 24px 60px rgba(0,0,0,0.3)',
  },
  logoWrap: {
    display: 'flex',
    alignItems: 'center',
    gap: 10,
    marginBottom: 28,
  },
  logoIcon: {
    width: 38,
    height: 38,
    borderRadius: 10,
    background: '#3b82f6',
    color: '#fff',
    fontSize: 20,
    fontWeight: 700,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  logoText: {
    fontSize: 20,
    fontWeight: 700,
    color: '#1e293b',
  },
  title: {
    fontSize: 26,
    fontWeight: 700,
    color: '#0f172a',
    margin: '0 0 6px',
  },
  sub: {
    fontSize: 14,
    color: '#64748b',
    margin: '0 0 28px',
  },
  form: {
    display: 'flex',
    flexDirection: 'column',
    gap: 16,
  },
  field: {
    display: 'flex',
    flexDirection: 'column',
    gap: 6,
  },
  label: {
    fontSize: 13,
    fontWeight: 600,
    color: '#374151',
  },
  input: {
    padding: '12px 14px',
    border: '1.5px solid #e2e8f0',
    borderRadius: 10,
    fontSize: 15,
    color: '#1e293b',
    outline: 'none',
    transition: 'border-color 0.2s',
  },
  error: {
    fontSize: 13,
    color: '#dc2626',
    background: '#fef2f2',
    border: '1px solid #fecaca',
    borderRadius: 8,
    padding: '10px 14px',
    margin: 0,
  },
  btn: {
    marginTop: 4,
    padding: '13px',
    background: '#3b82f6',
    color: '#fff',
    border: 'none',
    borderRadius: 10,
    fontSize: 16,
    fontWeight: 600,
    cursor: 'pointer',
    transition: 'background 0.2s',
  },
  backLink: {
    marginTop: 24,
    textAlign: 'center',
    fontSize: 13,
    color: '#94a3b8',
    cursor: 'pointer',
  },
}
