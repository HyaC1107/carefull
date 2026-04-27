import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { adminRequest, clearAdminToken, getAdminToken } from '../adminApi'

function decodeAdminToken() {
  const token = getAdminToken()
  if (!token) return null
  try {
    const payload = token.split('.')[1]
    return JSON.parse(atob(payload.replace(/-/g, '+').replace(/_/g, '/')))
  } catch {
    return null
  }
}

function StatCard({ label, value, color }) {
  return (
    <div style={{ ...s.statCard, borderTop: `4px solid ${color}` }}>
      <p style={s.statLabel}>{label}</p>
      <p style={{ ...s.statValue, color }}>{value ?? '-'}</p>
    </div>
  )
}

function Badge({ ok, trueLabel = 'Y', falseLabel = 'N' }) {
  return (
    <span style={{
      padding: '2px 10px',
      borderRadius: 20,
      fontSize: 12,
      fontWeight: 600,
      background: ok ? '#dcfce7' : '#fee2e2',
      color: ok ? '#16a34a' : '#dc2626',
    }}>
      {ok ? trueLabel : falseLabel}
    </span>
  )
}

export default function AdminDashboardPage() {
  const navigate = useNavigate()
  const admin    = decodeAdminToken()
  const [stats, setStats]       = useState(null)
  const [activities, setActivities] = useState([])
  const [tab, setTab]           = useState('overview')
  const [members, setMembers]   = useState([])
  const [loading, setLoading]   = useState(true)
  const [error, setError]       = useState('')

  useEffect(() => {
    loadStats()
  }, [])

  const loadStats = async () => {
    setLoading(true)
    setError('')
    try {
      const data = await adminRequest('/api/admin/stats')
      setStats(data.stats)
      setActivities(data.recent_activities || [])
    } catch (err) {
      if (err.status === 401 || err.status === 403) {
        handleLogout()
      } else {
        setError(err.message)
      }
    } finally {
      setLoading(false)
    }
  }

  const loadMembers = async () => {
    try {
      const data = await adminRequest('/api/admin/members')
      setMembers(data.members || [])
    } catch (err) {
      if (err.status === 401 || err.status === 403) handleLogout()
    }
  }

  const handleTabChange = (t) => {
    setTab(t)
    if (t === 'members' && members.length === 0) loadMembers()
  }

  const handleLogout = () => {
    clearAdminToken()
    navigate('/admin', { replace: true })
  }

  const fmt = (iso) => {
    if (!iso) return '-'
    return new Date(iso).toLocaleString('ko-KR', {
      month: '2-digit', day: '2-digit',
      hour: '2-digit', minute: '2-digit',
    })
  }

  return (
    <div style={s.page}>
      {/* 사이드바 */}
      <aside style={s.sidebar}>
        <div style={s.sideTop}>
          <div style={s.sideLogoRow}>
            <div style={s.sideLogo}>C</div>
            <span style={s.sideLogoText}>Carefull</span>
          </div>
          <p style={s.sideAdminBadge}>관리자 패널</p>
        </div>

        <nav style={s.nav}>
          {[
            { key: 'overview', label: '대시보드' },
            { key: 'activities', label: '복약 활동 로그' },
            { key: 'members', label: '회원 목록' },
          ].map(({ key, label }) => (
            <button
              key={key}
              style={{ ...s.navBtn, ...(tab === key ? s.navBtnActive : {}) }}
              onClick={() => handleTabChange(key)}
            >
              {label}
            </button>
          ))}
        </nav>

        <div style={s.sideBottom}>
          <p style={s.adminName}>{admin?.name ?? '관리자'}</p>
          <p style={s.adminRole}>{admin?.role ?? ''}</p>
          <button style={s.logoutBtn} onClick={handleLogout}>로그아웃</button>
        </div>
      </aside>

      {/* 메인 콘텐츠 */}
      <main style={s.main}>
        <div style={s.header}>
          <h1 style={s.headerTitle}>
            {tab === 'overview' && '대시보드'}
            {tab === 'activities' && '복약 활동 로그'}
            {tab === 'members' && '회원 목록'}
          </h1>
          <button style={s.refreshBtn} onClick={loadStats}>새로고침</button>
        </div>

        {error && <div style={s.errorBox}>{error}</div>}

        {loading ? (
          <div style={s.loadingWrap}>불러오는 중...</div>
        ) : (
          <>
            {/* 대시보드 탭 */}
            {tab === 'overview' && (
              <>
                <div style={s.statRow}>
                  <StatCard label="총 회원 수" value={stats?.total_members} color="#3b82f6" />
                  <StatCard label="총 환자 수" value={stats?.total_patients} color="#8b5cf6" />
                  <StatCard label="오늘 복약 활동" value={stats?.today_activities} color="#16a34a" />
                </div>

                <div style={s.section}>
                  <h2 style={s.sectionTitle}>최근 복약 활동</h2>
                  <ActivityTable rows={activities} fmt={fmt} />
                </div>
              </>
            )}

            {/* 활동 로그 탭 */}
            {tab === 'activities' && (
              <div style={s.section}>
                <ActivityTable rows={activities} fmt={fmt} />
              </div>
            )}

            {/* 회원 목록 탭 */}
            {tab === 'members' && (
              <div style={s.section}>
                <div style={s.tableWrap}>
                  <table style={s.table}>
                    <thead>
                      <tr>
                        {['닉네임', '이메일', '환자 수', '가입일'].map(h => (
                          <th key={h} style={s.th}>{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {members.length === 0 ? (
                        <tr><td colSpan={4} style={s.empty}>데이터 없음</td></tr>
                      ) : members.map(m => (
                        <tr key={m.mem_id} style={s.tr}>
                          <td style={s.td}>{m.nick}</td>
                          <td style={s.td}>{m.email || '-'}</td>
                          <td style={s.td}>{m.patient_count}</td>
                          <td style={s.td}>{fmt(m.created_at)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </>
        )}
      </main>
    </div>
  )
}

function ActivityTable({ rows, fmt }) {
  return (
    <div style={s.tableWrap}>
      <table style={s.table}>
        <thead>
          <tr>
            {['환자명', '보호자', '얼굴인증', '약 배출', '복약확인', '유사도', '시각'].map(h => (
              <th key={h} style={s.th}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.length === 0 ? (
            <tr><td colSpan={7} style={s.empty}>데이터 없음</td></tr>
          ) : rows.map((r, i) => (
            <tr key={r.activity_id ?? i} style={s.tr}>
              <td style={s.td}>{r.patient_name ?? '-'}</td>
              <td style={s.td}>{r.member_nick ?? '-'}</td>
              <td style={{ ...s.td, textAlign: 'center' }}><Badge ok={r.face_verified} trueLabel="인증" falseLabel="미인증" /></td>
              <td style={{ ...s.td, textAlign: 'center' }}><Badge ok={r.dispensed} trueLabel="완료" falseLabel="미완료" /></td>
              <td style={{ ...s.td, textAlign: 'center' }}><Badge ok={r.action_verified} trueLabel="확인" falseLabel="미확인" /></td>
              <td style={{ ...s.td, textAlign: 'center' }}>
                {r.similarity_score != null ? (r.similarity_score * 100).toFixed(1) + '%' : '-'}
              </td>
              <td style={s.td}>{fmt(r.created_at)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

const s = {
  page: { display: 'flex', minHeight: '100vh', background: '#f1f5f9', fontFamily: 'sans-serif' },

  // 사이드바
  sidebar: {
    width: 220,
    minWidth: 220,
    background: '#0f172a',
    display: 'flex',
    flexDirection: 'column',
    padding: '28px 0',
  },
  sideTop: { padding: '0 20px 24px', borderBottom: '1px solid #1e293b' },
  sideLogoRow: { display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 },
  sideLogo: {
    width: 32, height: 32, borderRadius: 8,
    background: '#3b82f6', color: '#fff',
    fontSize: 16, fontWeight: 700,
    display: 'flex', alignItems: 'center', justifyContent: 'center',
  },
  sideLogoText: { fontSize: 16, fontWeight: 700, color: '#fff' },
  sideAdminBadge: {
    fontSize: 11, color: '#64748b',
    background: '#1e293b', borderRadius: 6,
    padding: '3px 8px', display: 'inline-block', margin: 0,
  },
  nav: { flex: 1, padding: '16px 12px', display: 'flex', flexDirection: 'column', gap: 4 },
  navBtn: {
    width: '100%', textAlign: 'left',
    padding: '10px 14px', borderRadius: 8,
    border: 'none', background: 'transparent',
    color: '#94a3b8', fontSize: 14, fontWeight: 500, cursor: 'pointer',
  },
  navBtnActive: { background: '#1e293b', color: '#fff' },
  sideBottom: { padding: '16px 20px', borderTop: '1px solid #1e293b' },
  adminName: { color: '#fff', fontWeight: 600, fontSize: 14, margin: '0 0 2px' },
  adminRole: { color: '#64748b', fontSize: 12, margin: '0 0 12px' },
  logoutBtn: {
    width: '100%', padding: '8px',
    background: '#1e293b', color: '#94a3b8',
    border: '1px solid #334155', borderRadius: 8,
    fontSize: 13, cursor: 'pointer',
  },

  // 메인
  main: { flex: 1, padding: '32px 36px', overflowY: 'auto' },
  header: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 28 },
  headerTitle: { fontSize: 24, fontWeight: 700, color: '#0f172a', margin: 0 },
  refreshBtn: {
    padding: '8px 16px', background: '#fff',
    border: '1.5px solid #e2e8f0', borderRadius: 8,
    fontSize: 13, color: '#374151', cursor: 'pointer',
  },
  errorBox: {
    background: '#fef2f2', border: '1px solid #fecaca',
    color: '#dc2626', borderRadius: 10, padding: '12px 16px', marginBottom: 20,
  },
  loadingWrap: { textAlign: 'center', padding: 80, color: '#64748b', fontSize: 16 },

  // 스탯 카드
  statRow: { display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16, marginBottom: 28 },
  statCard: {
    background: '#fff', borderRadius: 14,
    padding: '22px 24px',
    boxShadow: '0 1px 4px rgba(0,0,0,0.06)',
  },
  statLabel: { fontSize: 13, color: '#64748b', margin: '0 0 8px', fontWeight: 500 },
  statValue: { fontSize: 36, fontWeight: 700, margin: 0 },

  // 테이블
  section: { background: '#fff', borderRadius: 14, padding: '24px', boxShadow: '0 1px 4px rgba(0,0,0,0.06)' },
  sectionTitle: { fontSize: 16, fontWeight: 700, color: '#0f172a', margin: '0 0 16px' },
  tableWrap: { overflowX: 'auto' },
  table: { width: '100%', borderCollapse: 'collapse', fontSize: 14 },
  th: {
    textAlign: 'left', padding: '10px 14px',
    background: '#f8fafc', color: '#64748b',
    fontWeight: 600, fontSize: 12,
    borderBottom: '1px solid #e2e8f0',
    whiteSpace: 'nowrap',
  },
  tr: { borderBottom: '1px solid #f1f5f9' },
  td: { padding: '12px 14px', color: '#374151', verticalAlign: 'middle' },
  empty: { padding: '40px', textAlign: 'center', color: '#94a3b8' },
}
