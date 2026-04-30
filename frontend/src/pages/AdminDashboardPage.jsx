import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { API_BASE_URL } from '../api'
import { adminRequest, clearAdminToken, getAdminToken, sendTestPush } from '../adminApi'

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
  { key: 'manage',     label: '🔧 등록 관리' },
  { key: 'test',       label: '🧪 이벤트 테스트' },
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

/* ─── 등록 관리 탭 ───────────────────────────────────────────────────────── */
const INNER_TABS = [
  { key: 'device',   label: '기기 등록 / 해제' },
  { key: 'schedule', label: '스케줄 관리' },
  { key: 'patient',  label: '환자 삭제' },
]

function TestManagement({ onRefreshStats }) {
  const [innerTab,    setInnerTab]    = useState('device')
  const [patients,    setPatients]    = useState([])
  const [devices,     setDevices]     = useState([])
  const [schedules,   setSchedules]   = useState([])
  const [medications, setMedications] = useState([])
  const [loading,     setLoading]     = useState(false)
  const [msg,         setMsg]         = useState(null)

  const [devForm,  setDevForm]  = useState({ device_uid: '', patient_id: '' })
  const [scheForm, setScheForm] = useState({
    patient_id: '', medi_id: '', time_to_take: '',
    start_date: new Date().toISOString().split('T')[0], end_date: '', dose_interval: '1',
  })

  useEffect(() => { loadAll() }, [])

  const loadAll = async () => {
    setLoading(true)
    // 각 요청 개별 처리 — 하나 실패해도 나머지는 표시
    const safe = (p) => p.catch(() => ({}))
    const [p, d, sc, m] = await Promise.all([
      safe(adminRequest('/api/admin/patients')),
      safe(adminRequest('/api/admin/devices')),
      safe(adminRequest('/api/admin/schedules')),
      safe(adminRequest('/api/admin/medications')),
    ])
    setPatients(p.patients     || [])
    setDevices(d.devices       || [])
    setSchedules(sc.schedules  || [])
    setMedications(m.medications || [])
    setLoading(false)
  }

  const flash = (ok, text) => {
    setMsg({ ok, text })
    setTimeout(() => setMsg(null), 5000)
  }

  const registerDevice = async (e) => {
    e.preventDefault()
    try {
      const d = await adminRequest('/api/admin/test/device', { method: 'POST', body: devForm })
      flash(true, d.message || '기기 등록 완료')
      setDevForm(p => ({ ...p, patient_id: '' }))
      loadAll()
    } catch (err) { flash(false, err.message) }
  }

  const deregisterDevice = async (device_uid) => {
    if (!window.confirm(`기기 "${device_uid}" 를 해제하시겠습니까?`)) return
    try {
      const d = await adminRequest(`/api/admin/test/device/${encodeURIComponent(device_uid)}`, { method: 'DELETE' })
      flash(true, d.message || '기기 해제 완료')
      loadAll()
    } catch (err) { flash(false, err.message) }
  }

  const addSchedule = async (e) => {
    e.preventDefault()
    try {
      const d = await adminRequest('/api/admin/test/schedule', { method: 'POST', body: scheForm })
      flash(true, `${d.message || '스케줄 추가 완료'} (sche_id: ${d.schedule?.sche_id})`)
      setScheForm(p => ({ ...p, time_to_take: '', end_date: '' }))
      loadAll()
    } catch (err) { flash(false, err.message) }
  }

  const deleteSchedule = async (sche_id, label) => {
    if (!window.confirm(`스케줄 "${label}" 을 삭제하시겠습니까?`)) return
    try {
      const d = await adminRequest(`/api/admin/test/schedule/${sche_id}`, { method: 'DELETE' })
      flash(true, d.message || '삭제 완료')
      loadAll()
    } catch (err) { flash(false, err.message) }
  }

  const deletePatient = async (patient_id, patient_name) => {
    if (!window.confirm(`"${patient_name}" 환자를 삭제하시겠습니까?\n스케줄·복약 기록·얼굴 데이터·기기 연결이 모두 삭제됩니다.`)) return
    try {
      const d = await adminRequest(`/api/admin/test/patient/${patient_id}`, { method: 'DELETE' })
      flash(true, d.message || '삭제 완료')
      loadAll()
      if (onRefreshStats) onRefreshStats()
    } catch (err) { flash(false, err.message) }
  }

  return (
    <div>
      {/* 알림 */}
      {msg && (
        <div style={{ ...s.resultBox, borderColor: msg.ok ? '#86efac' : '#fca5a5', background: msg.ok ? '#f0fdf4' : '#fef2f2', marginBottom: 16 }}>
          <p style={{ margin: 0, fontWeight: 600, color: msg.ok ? '#16a34a' : '#dc2626' }}>
            {msg.ok ? '✓ ' : '✗ '}{msg.text}
          </p>
        </div>
      )}

      {/* 내부 탭 바 */}
      <div style={s.innerTabBar}>
        {INNER_TABS.map(t => (
          <button key={t.key}
            style={{ ...s.innerTabBtn, ...(innerTab === t.key ? s.innerTabActive : {}) }}
            onClick={() => setInnerTab(t.key)}>
            {t.label}
          </button>
        ))}
        <button style={{ ...s.refreshBtn, marginLeft: 'auto' }} onClick={loadAll}>새로고침</button>
      </div>

      {loading && <div style={{ padding: '20px 0', color: '#64748b', fontSize: 14 }}>불러오는 중...</div>}

      {/* ── 기기 등록 / 해제 ── */}
      {innerTab === 'device' && (
        <div style={s.section}>
          <form onSubmit={registerDevice} style={{ display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'flex-end', marginBottom: 24 }}>
            <div style={s.testField}>
              <label style={s.testLabel}>기기 UID *</label>
              <input style={{ ...s.testInput, width: 300 }}
                placeholder="라즈베리파이 홈 화면 하단의 기기 UID"
                value={devForm.device_uid}
                onChange={e => setDevForm(p => ({ ...p, device_uid: e.target.value }))} required />
            </div>
            <div style={s.testField}>
              <label style={s.testLabel}>연결할 환자 *</label>
              <select style={{ ...s.testInput, width: 220 }}
                value={devForm.patient_id}
                onChange={e => setDevForm(p => ({ ...p, patient_id: e.target.value }))} required>
                <option value="">-- 환자 선택 --</option>
                {patients.map(p => (
                  <option key={p.patient_id} value={p.patient_id}>
                    {p.patient_name} ({p.member_nick || '?'})
                  </option>
                ))}
              </select>
            </div>
            <button style={s.testBtn} type="submit">기기 등록</button>
          </form>

          <Table
            headers={['기기 UID', '환자', '보호자', '상태', '마지막 핑', '등록일', '해제']}
            rows={devices}
            renderRow={(r, i) => (
              <tr key={r.device_id} style={i % 2 === 0 ? s.trEven : {}}>
                <td style={s.td}><code style={s.code}>{r.device_uid}</code></td>
                <td style={s.td}>{r.patient_name || <span style={{ color: '#94a3b8' }}>미연결</span>}</td>
                <td style={s.td}>{r.member_nick || '-'}</td>
                <td style={s.td}>{r.device_status}</td>
                <td style={s.td}>{fmt(r.last_ping)}</td>
                <td style={s.td}>{fmt(r.registered_at)}</td>
                <td style={s.td}>
                  {r.patient_name && (
                    <button style={s.dangerBtn} onClick={() => deregisterDevice(r.device_uid)}>해제</button>
                  )}
                </td>
              </tr>
            )}
          />
        </div>
      )}

      {/* ── 스케줄 관리 ── */}
      {innerTab === 'schedule' && (
        <div style={s.section}>
          <p style={{ fontSize: 12, color: '#64748b', marginTop: 0, marginBottom: 16 }}>
            추가 즉시 라즈베리파이가 30초 내 폴링해서 해당 시간에 알림을 울립니다.
          </p>
          <form onSubmit={addSchedule} style={{ display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'flex-end', marginBottom: 24 }}>
            <div style={s.testField}>
              <label style={s.testLabel}>환자 *</label>
              <select style={s.testInput} value={scheForm.patient_id}
                onChange={e => setScheForm(p => ({ ...p, patient_id: e.target.value }))} required>
                <option value="">-- 환자 선택 --</option>
                {patients.map(p => <option key={p.patient_id} value={p.patient_id}>{p.patient_name}</option>)}
              </select>
            </div>
            <div style={s.testField}>
              <label style={s.testLabel}>약 *</label>
              <select style={{ ...s.testInput, width: 200 }} value={scheForm.medi_id}
                onChange={e => setScheForm(p => ({ ...p, medi_id: e.target.value }))} required>
                <option value="">-- 약 선택 --</option>
                {medications.length === 0
                  ? <option disabled>약 목록 로드 실패 (medi_id 직접 입력 필요)</option>
                  : medications.map(m => <option key={m.medi_id} value={m.medi_id}>{m.medi_name}</option>)
                }
              </select>
            </div>
            <div style={s.testField}>
              <label style={s.testLabel}>복약 시간 *</label>
              <input style={s.testInput} type="time" value={scheForm.time_to_take}
                onChange={e => setScheForm(p => ({ ...p, time_to_take: e.target.value }))} required />
            </div>
            <div style={s.testField}>
              <label style={s.testLabel}>시작일 *</label>
              <input style={s.testInput} type="date" value={scheForm.start_date}
                onChange={e => setScheForm(p => ({ ...p, start_date: e.target.value }))} required />
            </div>
            <div style={s.testField}>
              <label style={s.testLabel}>종료일</label>
              <input style={s.testInput} type="date" value={scheForm.end_date}
                onChange={e => setScheForm(p => ({ ...p, end_date: e.target.value }))} />
            </div>
            <div style={s.testField}>
              <label style={s.testLabel}>복약 간격(일)</label>
              <select style={{ ...s.testInput, width: 90 }} value={scheForm.dose_interval}
                onChange={e => setScheForm(p => ({ ...p, dose_interval: e.target.value }))}>
                {[1,2,3,4,5].map(n => <option key={n} value={n}>{n}일</option>)}
              </select>
            </div>
            <button style={s.testBtn} type="submit">스케줄 추가</button>
          </form>

          <Table
            headers={['sche_id', '환자', '약 이름', '복약 시간', '시작일', '종료일', '간격', '상태', '삭제']}
            rows={schedules}
            renderRow={(r, i) => (
              <tr key={r.sche_id} style={i % 2 === 0 ? s.trEven : {}}>
                <td style={{ ...s.td, color: '#94a3b8', fontSize: 12 }}>{r.sche_id}</td>
                <td style={s.td}>{r.patient_name || '-'}</td>
                <td style={s.td}>{r.medi_name || '-'}</td>
                <td style={{ ...s.td, fontWeight: 700, color: '#3b82f6', fontSize: 15 }}>{r.time_to_take?.slice(0, 5) || '-'}</td>
                <td style={s.td}>{r.start_date ? new Date(r.start_date).toLocaleDateString('ko-KR') : '-'}</td>
                <td style={s.td}>{r.end_date ? new Date(r.end_date).toLocaleDateString('ko-KR') : '-'}</td>
                <td style={{ ...s.td, textAlign: 'center' }}>{r.dose_interval ?? '-'}일</td>
                <td style={s.td}><StatusBadge status={r.status} /></td>
                <td style={s.td}>
                  <button style={s.dangerBtn}
                    onClick={() => deleteSchedule(r.sche_id, `${r.patient_name} ${r.time_to_take?.slice(0,5)}`)}>
                    삭제
                  </button>
                </td>
              </tr>
            )}
          />
        </div>
      )}

      {/* ── 환자 삭제 ── */}
      {innerTab === 'patient' && (
        <div style={s.section}>
          <p style={{ fontSize: 12, color: '#ef4444', marginTop: 0, marginBottom: 16 }}>
            ⚠️ 삭제 시 스케줄·복약 기록·얼굴 데이터·기기 연결이 모두 삭제됩니다.
          </p>
          <Table
            headers={['patient_id', '환자명', '보호자', '기기 UID', '지문 ID', '등록일', '삭제']}
            rows={patients}
            renderRow={(r, i) => (
              <tr key={r.patient_id} style={i % 2 === 0 ? s.trEven : {}}>
                <td style={{ ...s.td, color: '#94a3b8', fontSize: 12 }}>{r.patient_id}</td>
                <td style={s.td}>{r.patient_name}</td>
                <td style={s.td}>{r.member_nick || '-'}</td>
                <td style={s.td}><code style={s.code}>{r.device_uid || '-'}</code></td>
                <td style={{ ...s.td, textAlign: 'center' }}>{r.fingerprint_id ?? '-'}</td>
                <td style={s.td}>{fmt(r.created_at)}</td>
                <td style={s.td}>
                  <button style={s.dangerBtn} onClick={() => deletePatient(r.patient_id, r.patient_name)}>삭제</button>
                </td>
              </tr>
            )}
          />
        </div>
      )}
    </div>
  )
}

/* ─── 기기 이벤트 테스트 폼 ─────────────────────────────────────────────── */
function DeviceEventTest() {
  const [members, setMembers] = useState([])
  const [form, setForm] = useState({
    device_uid: '', sche_id: '',
    face_verified: 'true', dispensed: 'true', action_verified: 'true',
    raw_confidence: '0.85', status: '',
  })
  const [pushForm, setPushForm] = useState({
    mem_id: '', title: '테스트 알림', body: '관리자 페이지에서 보내는 테스트 메시지입니다.',
  })
  const [result, setResult] = useState(null)
  const [pushResult, setPushResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [pushLoading, setPushLoading] = useState(false)

  useEffect(() => {
    adminRequest('/api/admin/members').then(d => setMembers(d.members || []))
  }, [])

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

  const handlePushSubmit = async (e) => {
    e.preventDefault()
    setPushLoading(true)
    setPushResult(null)
    try {
      const d = await sendTestPush(pushForm.mem_id, pushForm.title, pushForm.body)
      setPushResult({ ok: true, data: d })
    } catch (err) {
      setPushResult({ ok: false, data: { message: err.message } })
    } finally {
      setPushLoading(false)
    }
  }

  const Field = ({ label, name, type = 'text', placeholder, val, onChg }) => (
    <div style={s.testField}>
      <label style={s.testLabel}>{label}</label>
      <input style={s.testInput} type={type} placeholder={placeholder}
        value={val !== undefined ? val : form[name]} 
        onChange={e => onChg ? onChg(e.target.value) : set(name, e.target.value)} />
    </div>
  )

  const Select = ({ label, name, options, val, onChg }) => (
    <div style={s.testField}>
      <label style={s.testLabel}>{label}</label>
      <select style={s.testInput} value={val !== undefined ? val : form[name]} 
        onChange={e => onChg ? onChg(e.target.value) : set(name, e.target.value)}>
        {options.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>
    </div>
  )

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 40 }}>
      {/* 1. 기기 이벤트 시뮬레이션 */}
      <section>
        <h2 style={{ ...s.sectionTitle, borderLeft: '4px solid #3b82f6', paddingLeft: 12, marginBottom: 20 }}>기기 이벤트 시뮬레이션</h2>
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

        <div style={{ marginTop: 24 }}>
          <h3 style={{ fontSize: 14, color: '#374151', marginBottom: 12 }}>자주 쓰는 시나리오</h3>
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
      </section>

      <hr style={{ border: 'none', borderTop: '1px solid #e2e8f0', margin: 0 }} />

      {/* 2. 푸시 알림 테스트 */}
      <section>
        <h2 style={{ ...s.sectionTitle, borderLeft: '4px solid #f97316', paddingLeft: 12, marginBottom: 20 }}>FCM 푸시 알림 테스트</h2>
        <p style={{ color: '#64748b', fontSize: 14, marginBottom: 20 }}>
          특정 회원(보호자)에게 푸시 알림을 즉시 발송합니다. 해당 회원이 앱에서 알림 권한을 승인한 상태여야 합니다.
        </p>

        <form onSubmit={handlePushSubmit} style={s.testForm}>
          <div style={s.testGrid}>
            <Select label="수신 회원 (보호자) *" name="mem_id"
              val={pushForm.mem_id}
              onChg={v => setPushForm(p => ({ ...p, mem_id: v }))}
              options={[
                { value: '', label: '-- 회원 선택 --' },
                ...members.map(m => ({ value: m.mem_id, label: `${m.nick} (${m.email || '이메일 없음'})` }))
              ]} />
            <Field label="알림 제목 *" name="title"
              val={pushForm.title}
              onChg={v => setPushForm(p => ({ ...p, title: v }))}
              placeholder="알림 제목을 입력하세요" />
            <div style={{ ...s.testField, gridColumn: 'span 2' }}>
              <label style={s.testLabel}>알림 내용 *</label>
              <textarea style={{ ...s.testInput, height: 80, resize: 'none' }}
                value={pushForm.body}
                onChange={e => setPushForm(p => ({ ...p, body: e.target.value }))}
                placeholder="알림 내용을 입력하세요" required />
            </div>
          </div>

          <button style={{ ...s.testBtn, background: '#f97316', opacity: pushLoading ? 0.7 : 1 }} type="submit" disabled={pushLoading}>
            {pushLoading ? '발송 중...' : '테스트 푸시 발송'}
          </button>
        </form>

        {pushResult && (
          <div style={{ ...s.resultBox, borderColor: pushResult.ok ? '#86efac' : '#fca5a5', background: pushResult.ok ? '#f0fdf4' : '#fef2f2' }}>
            <p style={{ fontWeight: 700, color: pushResult.ok ? '#16a34a' : '#dc2626', margin: '0 0 8px' }}>
              {pushResult.ok ? '✓ 전송 요청 성공' : '✗ 전송 요청 실패'}
            </p>
            <pre style={s.pre}>{JSON.stringify(pushResult.data, null, 2)}</pre>
          </div>
        )}
      </section>
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
                  headers={['닉네임', '이메일', '로그인 방식', '환자 수']}
                  rows={data}
                  renderRow={(r, i) => (
                    <tr key={r.mem_id} style={i % 2 === 0 ? s.trEven : {}}>
                      <td style={s.td}>{r.nick}</td>
                      <td style={s.td}>{r.email || '-'}</td>
                      <td style={s.td}><span style={s.providerBadge}>{r.provider}</span></td>
                      <td style={{ ...s.td, textAlign: 'center' }}>{r.patient_count}</td>
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
                  headers={['기기 UID', '환자', '보호자', '마지막 핑', '상태', '등록일']}
                  rows={data}
                  renderRow={(r, i) => {
                    const online = r.last_ping && (Date.now() - new Date(r.last_ping).getTime()) < 5 * 60 * 1000
                    return (
                      <tr key={r.device_id} style={i % 2 === 0 ? s.trEven : {}}>
                        <td style={s.td}><code style={s.code}>{r.device_uid}</code></td>
                        <td style={s.td}>{r.patient_name || '-'}</td>
                        <td style={s.td}>{r.member_nick || '-'}</td>
                        <td style={s.td}>{fmt(r.last_ping)}</td>
                        <td style={s.td}>
                          <span style={{ padding: '2px 10px', borderRadius: 20, fontSize: 12, fontWeight: 600,
                            background: online ? '#dcfce7' : '#f1f5f9', color: online ? '#16a34a' : '#94a3b8' }}>
                            {online ? '온라인' : '오프라인'}
                          </span>
                        </td>
                        <td style={s.td}>{fmt(r.registered_at)}</td>
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
                  headers={['환자', '약 이름', '복약 시간', '시작일', '종료일', '복약 간격', '상태']}
                  rows={data}
                  renderRow={(r, i) => (
                    <tr key={r.sche_id} style={i % 2 === 0 ? s.trEven : {}}>
                      <td style={s.td}>{r.patient_name || '-'}</td>
                      <td style={s.td}>{r.medi_name || '-'}</td>
                      <td style={{ ...s.td, fontWeight: 600, color: '#3b82f6' }}>{r.time_to_take?.slice(0, 5) || '-'}</td>
                      <td style={s.td}>{r.start_date ? new Date(r.start_date).toLocaleDateString('ko-KR') : '-'}</td>
                      <td style={s.td}>{r.end_date ? new Date(r.end_date).toLocaleDateString('ko-KR') : '-'}</td>
                      <td style={{ ...s.td, textAlign: 'center' }}>{r.dose_interval ?? '-'}일</td>
                      <td style={s.td}><StatusBadge status={r.status} /></td>
                    </tr>
                  )}
                />
              </div>
            )}

            {/* 등록 관리 */}
            {tab === 'manage' && (
              <TestManagement onRefreshStats={loadStats} />
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
  dangerBtn: { padding: '4px 12px', background: '#fef2f2', border: '1px solid #fecaca', borderRadius: 6, fontSize: 12, color: '#dc2626', cursor: 'pointer', fontWeight: 600 },

  innerTabBar: { display: 'flex', alignItems: 'center', gap: 4, marginBottom: 16, borderBottom: '2px solid #e2e8f0', paddingBottom: 0 },
  innerTabBtn: { padding: '8px 18px', border: 'none', background: 'transparent', fontSize: 14, fontWeight: 500, color: '#64748b', cursor: 'pointer', borderBottom: '2px solid transparent', marginBottom: -2 },
  innerTabActive: { color: '#3b82f6', fontWeight: 700, borderBottom: '2px solid #3b82f6' },
}
