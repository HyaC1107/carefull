import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { API_BASE_URL } from '../api'
import { adminRequest, clearAdminToken, getAdminToken } from '../adminApi'

/* ─── JWT 디코딩 ─────────────────────────────────────────────────────────── */
function decodeAdminToken() {
  try {
    const payload = getAdminToken().split('.')[1]
    return JSON.parse(atob(payload.replace(/-/g, '+').replace(/_/g, '/')))
  } catch { return null }
}

/* ─── 공통 유틸 ──────────────────────────────────────────────────────────── */
const fmt = (iso) => {
  if (!iso) return '-'
  return new Date(iso).toLocaleString('ko-KR', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

const STATUS_COLOR = {
  SUCCESS: { bg: '#dcfce7', color: '#16a34a' },
  FAILED:  { bg: '#fee2e2', color: '#dc2626' },
  MISSED:  { bg: '#fef3c7', color: '#d97706' },
  ERROR:   { bg: '#f3e8ff', color: '#7c3aed' },
}

function StatusBadge({ status }) {
  const c = STATUS_COLOR[status] || { bg: '#f1f5f9', color: '#64748b' }
  return (
    <span style={{ padding: '2px 10px', borderRadius: 20, fontSize: 12, fontWeight: 600, background: c.bg, color: c.color }}>
      {status || '-'}
    </span>
  )
}

function BoolBadge({ val, trueLabel = 'Y', falseLabel = 'N' }) {
  return (
    <span style={{ padding: '2px 10px', borderRadius: 20, fontSize: 12, fontWeight: 600,
      background: val ? '#dcfce7' : '#f1f5f9', color: val ? '#16a34a' : '#94a3b8' }}>
      {val ? trueLabel : falseLabel}
    </span>
  )
}

/* ─── 탭 목록 ────────────────────────────────────────────────────────────── */
const TABS = [
  { key: 'overview',   label: '대시보드' },
  { key: 'activities', label: '복약 로그' },
  { key: 'members',    label: '회원 목록' },
  { key: 'patients',   label: '환자 목록' },
  { key: 'devices',    label: '기기 목록' },
  { key: 'schedules',  label: '스케줄 목록' },
  { key: 'test',       label: '🧪 기기 이벤트 테스트' },
]

/* ─── 테이블 공통 래퍼 ───────────────────────────────────────────────────── */
function Table({ headers, rows, empty = '데이터 없음', renderRow }) {
  return (
    <div style={{ overflowX: 'auto' }}>
      <table style={s.table}>
        <thead>
          <tr>{headers.map(h => <th key={h} style={s.th}>{h}</th>)}</tr>
        </thead>
        <tbody>
          {rows.length === 0
            ? <tr><td colSpan={headers.length} style={s.empty}>{empty}</td></tr>
            : rows.map((r, i) => renderRow(r, i))}
        </tbody>
      </table>
    </div>
  )
}

/* ─── 기기 이벤트 테스트 폼 ─────────────────────────────────────────────── */
function DeviceEventTest() {
  const [form, setForm] = useState({
    device_uid: '', sche_id: '',
    face_verified: 'true', dispensed: 'true', action_verified: 'true',
    raw_confidence: '0.85', status: '',
  })
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)

  const set = (k, v) => setForm(prev => ({ ...prev, [k]: v }))

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setResult(null)
    try {
      const body = {
        device_uid:       form.device_uid,
        sche_id:          parseInt(form.sche_id, 10),
        face_verified:    form.face_verified === 'true',
        dispensed:        form.dispensed === 'true',
        action_verified:  form.action_verified === 'true',
        raw_confidence:   parseFloat(form.raw_confidence),
      }
      if (form.status) body.status = form.status

      const res = await fetch(new URL('/api/log/device-event', API_BASE_URL), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      const data = await res.json()
      setResult({ ok: res.ok, data })
    } catch (err) {
      setResult({ ok: false, data: { message: err.message } })
    } finally {
      setLoading(false)
    }
  }

  const Field = ({ label, name, type = 'text', placeholder }) => (
    <div style={s.testField}>
      <label style={s.testLabel}>{label}</label>
      <input style={s.testInput} type={type} placeholder={placeholder}
        value={form[name]} onChange={e => set(name, e.target.value)} />
    </div>
  )

  const Select = ({ label, name, options }) => (
    <div style={s.testField}>
      <label style={s.testLabel}>{label}</label>
      <select style={s.testInput} value={form[name]} onChange={e => set(name, e.target.value)}>
        {options.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>
    </div>
  )

  return (
    <div>
      <p style={{ color: '#64748b', fontSize: 14, marginBottom: 20 }}>
        라즈베리파이 디바이스 이벤트를 시뮬레이션합니다. <code style={s.code}>POST /api/log/device-event</code>
      </p>

      <form onSubmit={handleSubmit} style={s.testForm}>
        <div style={s.testGrid}>
          <Field label="device_uid *" name="device_uid" placeholder="등록된 기기 UID" />
          <Field label="sche_id *" name="sche_id" type="number" placeholder="스케줄 ID" />
          <Field label="raw_confidence (0~1)" name="raw_confidence" type="number" placeholder="0.85" />
          <Field label="status (선택, 비우면 자동결정)" name="status" placeholder="SUCCESS / FAILED / ERROR" />
          <Select label="face_verified (얼굴인증)" name="face_verified"
            options={[{ value: 'true', label: '성공 (true)' }, { value: 'false', label: '실패 (false)' }]} />
          <Select label="dispensed (약 배출)" name="dispensed"
            options={[{ value: 'true', label: '완료 (true)' }, { value: 'false', label: '실패 (false)' }]} />
          <Select label="action_verified (복약 확인)" name="action_verified"
            options={[{ value: 'true', label: '확인 (true)' }, { value: 'false', label: '미확인 (false)' }]} />
        </div>

        <button style={{ ...s.testBtn, opacity: loading ? 0.7 : 1 }} type="submit" disabled={loading}>
          {loading ? '전송 중...' : '이벤트 전송'}
        </button>
      </form>

      {result && (
        <div style={{ ...s.resultBox, borderColor: result.ok ? '#86efac' : '#fca5a5', background: result.ok ? '#f0fdf4' : '#fef2f2' }}>
          <p style={{ fontWeight: 700, color: result.ok ? '#16a34a' : '#dc2626', margin: '0 0 8px' }}>
            {result.ok ? '✓ 성공' : '✗ 실패'}
          </p>
          <pre style={s.pre}>{JSON.stringify(result.data, null, 2)}</pre>
        </div>
      )}

      <div style={{ marginTop: 32 }}>
        <h3 style={{ fontSize: 15, color: '#374151', marginBottom: 12 }}>자주 쓰는 시나리오</h3>
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
          {[
            { label: '정상 복약', vals: { face_verified: 'true', dispensed: 'true', action_verified: 'true', raw_confidence: '0.92' }},
            { label: '얼굴인증 실패', vals: { face_verified: 'false', dispensed: 'true', action_verified: 'true', raw_confidence: '0.3' }},
            { label: '복약 미확인', vals: { face_verified: 'true', dispensed: 'true', action_verified: 'false', raw_confidence: '0.85' }},
            { label: '전체 실패', vals: { face_verified: 'false', dispensed: 'false', action_verified: 'false', raw_confidence: '0.0' }},
          ].map(({ label, vals }) => (
            <button key={label} style={s.scenarioBtn}
              onClick={() => setForm(prev => ({ ...prev, ...vals }))}>
              {label}
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}

/* ─── 메인 컴포넌트 ───────────────────────────────────────────────────────── */
export default function AdminDashboardPage() {
  const navigate = useNavigate()
  const admin    = decodeAdminToken()
  const [tab, setTab]             = useState('overview')
  const [stats, setStats]         = useState(null)
  const [recentActs, setRecentActs] = useState([])
  const [data, setData]           = useState([])
  const [total, setTotal]         = useState(0)
  const [offset, setOffset]       = useState(0)
  const [loading, setLoading]     = useState(false)
  const [error, setError]         = useState('')
  const LIMIT = 50

  useEffect(() => { loadStats() }, [])
  useEffect(() => { if (tab !== 'overview' && tab !== 'test') loadTab(tab, 0) }, [tab])

  const handleLogout = () => { clearAdminToken(); navigate('/admin', { replace: true }) }

  const authFail = (err) => {
    if (err.status === 401 || err.status === 403) handleLogout()
    else setError(err.message)
  }

  const loadStats = async () => {
    setLoading(true); setError('')
    try {
      const d = await adminRequest('/api/admin/stats')
      setStats(d.stats)
      setRecentActs(d.recent_activities || [])
    } catch (err) { authFail(err) }
    finally { setLoading(false) }
  }

  const loadTab = async (t, off = 0) => {
    setLoading(true); setError('')
    try {
      const ep = {
        activities: `/api/admin/activities?limit=${LIMIT}&offset=${off}`,
        members:    '/api/admin/members',
        patients:   '/api/admin/patients',
        devices:    '/api/admin/devices',
        schedules:  '/api/admin/schedules',
      }[t]
      const d = await adminRequest(ep)
      const key = { activities: 'activities', members: 'members', patients: 'patients', devices: 'devices', schedules: 'schedules' }[t]
      setData(d[key] || [])
      setTotal(d.total || d[key]?.length || 0)
      setOffset(off)
    } catch (err) { authFail(err) }
    finally { setLoading(false) }
  }

  const handleTabChange = (t) => { setTab(t); setData([]); setOffset(0) }

  return (
    <div style={s.page}>
      {/* ── 사이드바 ── */}
      <aside style={s.sidebar}>
        <div style={s.sideTop}>
          <div style={s.sideLogoRow}>
            <div style={s.sideLogo}>C</div>
            <span style={s.sideLogoText}>Carefull</span>
          </div>
          <span style={s.sideAdminBadge}>관리자 패널</span>
        </div>

        <nav style={s.nav}>
          {TABS.map(({ key, label }) => (
            <button key={key} style={{ ...s.navBtn, ...(tab === key ? s.navActive : {}) }}
              onClick={() => handleTabChange(key)}>
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

      {/* ── 메인 ── */}
      <main style={s.main}>
        <div style={s.header}>
          <h1 style={s.headerTitle}>{TABS.find(t => t.key === tab)?.label}</h1>
          <div style={{ display: 'flex', gap: 8 }}>
            {tab === 'activities' && total > 0 && (
              <span style={{ fontSize: 13, color: '#64748b', alignSelf: 'center' }}>총 {total}건</span>
            )}
            <button style={s.refreshBtn} onClick={() => tab === 'overview' ? loadStats() : loadTab(tab, offset)}>
              새로고침
            </button>
          </div>
        </div>

        {error && <div style={s.errorBox}>{error}</div>}
        {loading && <div style={s.loadingWrap}>불러오는 중...</div>}

        {!loading && (
          <>
            {/* 대시보드 */}
            {tab === 'overview' && <>
              <div style={s.statRow}>
                {[
                  { label: '총 회원', value: stats?.total_members,    color: '#3b82f6' },
                  { label: '총 환자', value: stats?.total_patients,   color: '#8b5cf6' },
                  { label: '등록 기기', value: stats?.total_devices,  color: '#f97316' },
                  { label: '오늘 활동', value: stats?.today_activities, color: '#16a34a' },
                ].map(({ label, value, color }) => (
                  <div key={label} style={{ ...s.statCard, borderTop: `4px solid ${color}` }}>
                    <p style={s.statLabel}>{label}</p>
                    <p style={{ ...s.statValue, color }}>{value ?? '-'}</p>
                  </div>
                ))}
              </div>
              <div style={s.section}>
                <h2 style={s.sectionTitle}>최근 복약 활동 (최신 20건)</h2>
                <ActivityTable rows={recentActs} />
              </div>
            </>}

            {/* 복약 로그 */}
            {tab === 'activities' && <>
              <div style={s.section}>
                <ActivityTable rows={data} />
                {total > LIMIT && (
                  <div style={s.pagination}>
                    <button style={s.pageBtn} disabled={offset === 0}
                      onClick={() => loadTab(tab, Math.max(0, offset - LIMIT))}>이전</button>
                    <span style={{ fontSize: 13, color: '#64748b' }}>
                      {offset + 1} - {Math.min(offset + LIMIT, total)} / {total}
                    </span>
                    <button style={s.pageBtn} disabled={offset + LIMIT >= total}
                      onClick={() => loadTab(tab, offset + LIMIT)}>다음</button>
                  </div>
                )}
              </div>
            </>}

            {/* 회원 목록 */}
            {tab === 'members' && (
              <div style={s.section}>
                <Table
                  headers={['닉네임', '이메일', '로그인 방식', '환자 수', '가입일']}
                  rows={data}
                  renderRow={(r, i) => (
                    <tr key={r.mem_id} style={i % 2 === 0 ? s.trEven : {}}>
                      <td style={s.td}>{r.nick}</td>
                      <td style={s.td}>{r.email || '-'}</td>
                      <td style={s.td}><span style={s.providerBadge}>{r.provider}</span></td>
                      <td style={{ ...s.td, textAlign: 'center' }}>{r.patient_count}</td>
                      <td style={s.td}>{fmt(r.created_at)}</td>
                    </tr>
                  )}
                />
              </div>
            )}

            {/* 환자 목록 */}
            {tab === 'patients' && (
              <div style={s.section}>
                <Table
                  headers={['환자명', '생년월일', '성별', '혈액형', '보호자(닉네임)', '기기 UID', '마지막 핑', '등록일']}
                  rows={data}
                  renderRow={(r, i) => (
                    <tr key={r.patient_id} style={i % 2 === 0 ? s.trEven : {}}>
                      <td style={s.td}>{r.patient_name}</td>
                      <td style={s.td}>{r.birthdate ? new Date(r.birthdate).toLocaleDateString('ko-KR') : '-'}</td>
                      <td style={s.td}>{r.gender || '-'}</td>
                      <td style={s.td}>{r.bloodtype || '-'}</td>
                      <td style={s.td}>{r.member_nick || '-'}</td>
                      <td style={s.td}><code style={s.code}>{r.device_uid || '-'}</code></td>
                      <td style={s.td}>{fmt(r.last_ping)}</td>
                      <td style={s.td}>{fmt(r.created_at)}</td>
                    </tr>
                  )}
                />
              </div>
            )}

            {/* 기기 목록 */}
            {tab === 'devices' && (
              <div style={s.section}>
                <Table
                  headers={['기기 UID', '기기명', '환자', '보호자', '마지막 핑', '상태', '등록일']}
                  rows={data}
                  renderRow={(r, i) => {
                    const online = r.last_ping && (Date.now() - new Date(r.last_ping).getTime()) < 5 * 60 * 1000
                    return (
                      <tr key={r.device_id} style={i % 2 === 0 ? s.trEven : {}}>
                        <td style={s.td}><code style={s.code}>{r.device_uid}</code></td>
                        <td style={s.td}>{r.device_name || '-'}</td>
                        <td style={s.td}>{r.patient_name || '-'}</td>
                        <td style={s.td}>{r.member_nick || '-'}</td>
                        <td style={s.td}>{fmt(r.last_ping)}</td>
                        <td style={s.td}>
                          <span style={{ padding: '2px 10px', borderRadius: 20, fontSize: 12, fontWeight: 600,
                            background: online ? '#dcfce7' : '#f1f5f9', color: online ? '#16a34a' : '#94a3b8' }}>
                            {online ? '온라인' : '오프라인'}
                          </span>
                        </td>
                        <td style={s.td}>{fmt(r.created_at)}</td>
                      </tr>
                    )
                  }}
                />
              </div>
            )}

            {/* 스케줄 목록 */}
            {tab === 'schedules' && (
              <div style={s.section}>
                <Table
                  headers={['환자', '약 이름', '복약 시간', '시작일', '종료일', '1회 용량', '등록일']}
                  rows={data}
                  renderRow={(r, i) => (
                    <tr key={r.sche_id} style={i % 2 === 0 ? s.trEven : {}}>
                      <td style={s.td}>{r.patient_name || '-'}</td>
                      <td style={s.td}>{r.medi_name || '-'}</td>
                      <td style={{ ...s.td, fontWeight: 600, color: '#3b82f6' }}>{r.time_to_take?.slice(0, 5) || '-'}</td>
                      <td style={s.td}>{r.start_date ? new Date(r.start_date).toLocaleDateString('ko-KR') : '-'}</td>
                      <td style={s.td}>{r.end_date ? new Date(r.end_date).toLocaleDateString('ko-KR') : '-'}</td>
                      <td style={s.td}>{r.dose_quantity ?? '-'}</td>
                      <td style={s.td}>{fmt(r.created_at)}</td>
                    </tr>
                  )}
                />
              </div>
            )}

            {/* 기기 이벤트 테스트 */}
            {tab === 'test' && (
              <div style={s.section}>
                <DeviceEventTest />
              </div>
            )}
          </>
        )}
      </main>
    </div>
  )
}

function ActivityTable({ rows }) {
  return (
    <Table
      headers={['환자', '보호자', '상태', '얼굴인증', '복약확인', '유사도', '스케줄시간', '실제시간', '기록일시']}
      rows={rows}
      renderRow={(r, i) => (
        <tr key={r.activity_id ?? i} style={i % 2 === 0 ? s.trEven : {}}>
          <td style={s.td}>{r.patient_name ?? '-'}</td>
          <td style={s.td}>{r.member_nick ?? '-'}</td>
          <td style={s.td}><StatusBadge status={r.status} /></td>
          <td style={{ ...s.td, textAlign: 'center' }}><BoolBadge val={r.is_face_auth} trueLabel="인증" falseLabel="미인증" /></td>
          <td style={{ ...s.td, textAlign: 'center' }}><BoolBadge val={r.is_ai_check} trueLabel="확인" falseLabel="미확인" /></td>
          <td style={{ ...s.td, textAlign: 'center' }}>
            {r.similarity_score != null ? (r.similarity_score * 100).toFixed(1) + '%' : '-'}
          </td>
          <td style={s.td}>{fmt(r.sche_time)}</td>
          <td style={s.td}>{fmt(r.actual_time)}</td>
          <td style={s.td}>{fmt(r.created_at)}</td>
        </tr>
      )}
    />
  )
}

/* ─── 스타일 ─────────────────────────────────────────────────────────────── */
const s = {
  page: { display: 'flex', minHeight: '100vh', background: '#f1f5f9', fontFamily: 'sans-serif' },

  sidebar: { width: 230, minWidth: 230, background: '#0f172a', display: 'flex', flexDirection: 'column', padding: '24px 0' },
  sideTop: { padding: '0 18px 20px', borderBottom: '1px solid #1e293b' },
  sideLogoRow: { display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 },
  sideLogo: { width: 32, height: 32, borderRadius: 8, background: '#3b82f6', color: '#fff', fontSize: 16, fontWeight: 700, display: 'flex', alignItems: 'center', justifyContent: 'center' },
  sideLogoText: { fontSize: 16, fontWeight: 700, color: '#fff' },
  sideAdminBadge: { fontSize: 11, color: '#64748b', background: '#1e293b', borderRadius: 6, padding: '3px 8px', display: 'inline-block' },
  nav: { flex: 1, padding: '12px 10px', display: 'flex', flexDirection: 'column', gap: 2 },
  navBtn: { width: '100%', textAlign: 'left', padding: '9px 12px', borderRadius: 8, border: 'none', background: 'transparent', color: '#94a3b8', fontSize: 13, fontWeight: 500, cursor: 'pointer' },
  navActive: { background: '#1e293b', color: '#fff' },
  sideBottom: { padding: '14px 18px', borderTop: '1px solid #1e293b' },
  adminName: { color: '#fff', fontWeight: 600, fontSize: 14, margin: '0 0 2px' },
  adminRole: { color: '#64748b', fontSize: 12, margin: '0 0 10px' },
  logoutBtn: { width: '100%', padding: '8px', background: '#1e293b', color: '#94a3b8', border: '1px solid #334155', borderRadius: 8, fontSize: 13, cursor: 'pointer' },

  main: { flex: 1, padding: '28px 32px', overflowY: 'auto', minWidth: 0 },
  header: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 },
  headerTitle: { fontSize: 22, fontWeight: 700, color: '#0f172a', margin: 0 },
  refreshBtn: { padding: '7px 14px', background: '#fff', border: '1.5px solid #e2e8f0', borderRadius: 8, fontSize: 13, color: '#374151', cursor: 'pointer' },
  errorBox: { background: '#fef2f2', border: '1px solid #fecaca', color: '#dc2626', borderRadius: 10, padding: '12px 16px', marginBottom: 20 },
  loadingWrap: { textAlign: 'center', padding: 80, color: '#64748b', fontSize: 15 },

  statRow: { display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 14, marginBottom: 24 },
  statCard: { background: '#fff', borderRadius: 14, padding: '20px 22px', boxShadow: '0 1px 4px rgba(0,0,0,0.06)' },
  statLabel: { fontSize: 12, color: '#64748b', margin: '0 0 6px', fontWeight: 500 },
  statValue: { fontSize: 32, fontWeight: 700, margin: 0 },

  section: { background: '#fff', borderRadius: 14, padding: '22px', boxShadow: '0 1px 4px rgba(0,0,0,0.06)', marginBottom: 16 },
  sectionTitle: { fontSize: 15, fontWeight: 700, color: '#0f172a', margin: '0 0 14px' },

  table: { width: '100%', borderCollapse: 'collapse', fontSize: 13 },
  th: { textAlign: 'left', padding: '9px 12px', background: '#f8fafc', color: '#64748b', fontWeight: 600, fontSize: 11, borderBottom: '1px solid #e2e8f0', whiteSpace: 'nowrap' },
  tr: {},
  trEven: { background: '#fafbfc' },
  td: { padding: '11px 12px', color: '#374151', verticalAlign: 'middle', borderBottom: '1px solid #f1f5f9' },
  empty: { padding: '40px', textAlign: 'center', color: '#94a3b8' },

  code: { background: '#f1f5f9', padding: '2px 6px', borderRadius: 4, fontSize: 12, fontFamily: 'monospace', color: '#475569' },
  providerBadge: { background: '#eff6ff', color: '#3b82f6', borderRadius: 20, padding: '2px 10px', fontSize: 12, fontWeight: 600 },

  pagination: { display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 14, marginTop: 16 },
  pageBtn: { padding: '6px 16px', background: '#f1f5f9', border: '1px solid #e2e8f0', borderRadius: 8, fontSize: 13, cursor: 'pointer', color: '#374151' },

  // 테스트 폼
  testForm: { marginBottom: 24 },
  testGrid: { display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '12px 20px', marginBottom: 20 },
  testField: { display: 'flex', flexDirection: 'column', gap: 5 },
  testLabel: { fontSize: 12, fontWeight: 600, color: '#374151' },
  testInput: { padding: '9px 12px', border: '1.5px solid #e2e8f0', borderRadius: 8, fontSize: 14, color: '#1e293b', outline: 'none', background: '#fff' },
  testBtn: { padding: '11px 28px', background: '#3b82f6', color: '#fff', border: 'none', borderRadius: 10, fontSize: 15, fontWeight: 600, cursor: 'pointer' },
  resultBox: { marginTop: 20, border: '1.5px solid', borderRadius: 12, padding: '16px' },
  pre: { margin: 0, fontSize: 12, fontFamily: 'monospace', overflowX: 'auto', color: '#374151', whiteSpace: 'pre-wrap' },
  scenarioBtn: { padding: '7px 14px', background: '#f8fafc', border: '1.5px solid #e2e8f0', borderRadius: 8, fontSize: 13, cursor: 'pointer', color: '#374151' },
}
