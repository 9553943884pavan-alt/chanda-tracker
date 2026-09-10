import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import api from '../api'
import { useAuth } from '../context/useAuth'

const initialFilters = { year: '', branch: '', gender: '' }

function errorMessage(error, fallback) {
  return error.response?.data?.detail || fallback
}

function StatusBadge({ status }) {
  const styles = {
    pending: 'bg-amber-50 text-amber-800 ring-amber-200',
    verified: 'bg-emerald-50 text-emerald-800 ring-emerald-200',
    rejected: 'bg-red-50 text-red-800 ring-red-200',
  }
  return <span className={`inline-flex rounded-full px-3 py-1 text-xs font-bold capitalize ring-1 ${styles[status] || 'bg-stone-100 text-stone-700 ring-stone-200'}`}>{status}</span>
}

function filterParams(filters) {
  return Object.fromEntries(Object.entries(filters).filter(([, value]) => value !== ''))
}

export default function AdminDashboard() {
  const { logout } = useAuth()
  const [filters, setFilters] = useState(initialFilters)
  const [payments, setPayments] = useState(null)
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [broadcasting, setBroadcasting] = useState(false)
  const [broadcastMessage, setBroadcastMessage] = useState('')
  const [broadcastRole, setBroadcastRole] = useState('all')

  async function loadStats() {
    try {
      const { data } = await api.get('/admin/stats')
      setStats(data)
    } catch (requestError) {
      console.error('Failed to load stats:', requestError)
    }
  }

  async function loadPayments(nextFilters = filters) {
    setLoading(true)
    try {
      const { data } = await api.get('/admin/payments', { params: filterParams(nextFilters) })
      setPayments(data)
      setError('')
    } catch (requestError) {
      setPayments([])
      setError(errorMessage(requestError, 'Unable to load payments.'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadPayments()
    loadStats()
  }, [])


  function updateFilter(event) {
    const nextFilters = { ...filters, [event.target.name]: event.target.value }
    setFilters(nextFilters)
    loadPayments(nextFilters)
  }

  async function sendBroadcast(event) {
    event.preventDefault()
    setError('')
    setMessage('')
    setBroadcasting(true)
    try {
      const { data } = await api.post('/admin/broadcast', {
        filter_year: filters.year ? Number(filters.year) : null,
        filter_branch: filters.branch || null,
        filter_gender: filters.gender || null,
        filter_role: broadcastRole,
        message: broadcastMessage,
      })
      setMessage(`${data.message}. Sent to ${data.recipient_count} user${data.recipient_count === 1 ? '' : 's'}.`)
      setBroadcastMessage('')
    } catch (requestError) {
      setError(errorMessage(requestError, 'Unable to send broadcast.'))
    } finally {
      setBroadcasting(false)
    }
  }

  return (
    <main className="min-h-screen px-5 py-6 sm:px-10">
      <nav className="mx-auto flex max-w-6xl items-center justify-between border-b border-stone-200 pb-5">
        <Link to="/admin-dashboard" className="font-display text-xl font-semibold tracking-tight text-stone-950">chanda<span className="text-teal-700">.</span></Link>
        <button type="button" onClick={logout} className="text-sm font-semibold text-stone-500 transition hover:text-stone-950">Sign out</button>
      </nav>
      <header className="mx-auto max-w-6xl pb-8 pt-12">
        <p className="text-xs font-bold uppercase tracking-[0.24em] text-teal-700">Admin workspace</p>
        <h1 className="mt-3 font-display text-5xl font-semibold tracking-tight text-stone-950">Keep the whole picture.</h1>
        <p className="mt-4 max-w-xl text-lg leading-8 text-stone-500">Review every contribution and reach the right people when something changes.</p>
        {stats && (
          <div className="mt-8 grid gap-4 grid-cols-2 lg:grid-cols-4">
            <div className="rounded-2xl border border-stone-200 bg-[#fffdf8] p-5 shadow-sm">
              <p className="text-xs font-bold uppercase tracking-wider text-stone-400">Total Collected</p>
              <p className="mt-2 text-3xl font-display font-bold text-teal-800">₹{stats.total_collected.toFixed(2)}</p>
              <p className="mt-1 text-xs text-stone-500">{stats.verified_count} verified payments</p>
            </div>
            <div className="rounded-2xl border border-stone-200 bg-[#fffdf8] p-5 shadow-sm">
              <p className="text-xs font-bold uppercase tracking-wider text-stone-400">Pending Verification</p>
              <p className="mt-2 text-3xl font-display font-bold text-amber-700">₹{stats.total_pending.toFixed(2)}</p>
              <p className="mt-1 text-xs text-stone-500">{stats.pending_count} pending reviews</p>
            </div>
            <div className="rounded-2xl border border-stone-200 bg-[#fffdf8] p-5 shadow-sm">
              <p className="text-xs font-bold uppercase tracking-wider text-stone-400">Active Collectors</p>
              <p className="mt-2 text-3xl font-display font-bold text-stone-900">{stats.active_collectors} / {stats.total_collectors}</p>
              <p className="mt-1 text-xs text-stone-500">With uploaded QR codes</p>
            </div>
            <div className="rounded-2xl border border-stone-200 bg-[#fffdf8] p-5 shadow-sm">
              <p className="text-xs font-bold uppercase tracking-wider text-stone-400">Registered Givers</p>
              <p className="mt-2 text-3xl font-display font-bold text-stone-900">{stats.total_givers}</p>
              <p className="mt-1 text-xs text-stone-500">IIITA Students</p>
            </div>
          </div>
        )}
      </header>
      <div className="mx-auto max-w-6xl space-y-8">

        <section className="rounded-2xl border border-stone-200 bg-[#fffdf8]/85 p-5 shadow-[0_18px_50px_rgba(56,73,64,0.08)] sm:p-7">
          <div className="flex flex-wrap items-end justify-between gap-5">
            <div><h2 className="font-display text-2xl font-semibold text-stone-950">Payment overview</h2><p className="mt-1 text-sm text-stone-500">Filters update the payment list immediately.</p></div>
            <div className="grid w-full gap-3 sm:grid-cols-3 sm:w-auto">
              <label className="field-label">Year<select className="field-input min-w-28" name="year" value={filters.year} onChange={updateFilter}><option value="">All years</option>{[1, 2, 3, 4].map((year) => <option key={year} value={year}>{year}</option>)}</select></label>
              <label className="field-label">Branch<select className="field-input min-w-28" name="branch" value={filters.branch} onChange={updateFilter}><option value="">All branches</option><option value="IT">IT</option><option value="ECE">ECE</option></select></label>
              <label className="field-label">Gender<select className="field-input min-w-28" name="gender" value={filters.gender} onChange={updateFilter}><option value="">All genders</option><option value="M">M</option><option value="F">F</option></select></label>
            </div>
          </div>
          {loading ? <p className="py-10 text-center text-sm text-stone-500">Loading payments...</p> : payments?.length ? <div className="mt-7 overflow-x-auto"><table className="w-full min-w-[1100px] text-left text-sm"><thead className="border-b border-stone-200 text-xs uppercase tracking-wider text-stone-500"><tr><th className="pb-3 pr-4">Giver</th><th className="pb-3 pr-4">Collector</th><th className="pb-3 pr-4">Group</th><th className="pb-3 pr-4">Amount</th><th className="pb-3 pr-4">Reference</th><th className="pb-3 pr-4">Status</th><th className="pb-3">Proof</th></tr></thead><tbody className="divide-y divide-stone-100">{payments.map((payment) => <tr key={payment.id}><td className="py-4 pr-4 font-semibold text-stone-800">{payment.giver_full_name}</td><td className="py-4 pr-4 font-semibold text-stone-800">{payment.collector_full_name}</td><td className="py-4 pr-4 text-xs text-stone-600">Y{payment.year} · {payment.branch || 'All branches'} · {payment.gender}</td><td className="py-4 pr-4 font-bold text-stone-800">{Number(payment.amount).toFixed(2)}</td><td className="py-4 pr-4 font-mono text-xs text-stone-600">{payment.transaction_ref}</td><td className="py-4 pr-4"><StatusBadge status={payment.status} /></td><td className="py-4"><a className="font-bold text-teal-800 hover:text-teal-950" href={payment.screenshot_url} target="_blank" rel="noreferrer">View Screenshot</a></td></tr>)}</tbody></table></div> : <p className="py-10 text-center text-sm text-stone-500">No payments match these filters.</p>}
        </section>
        <section className="rounded-2xl border border-stone-200 bg-[#fffdf8]/85 p-5 shadow-[0_18px_50px_rgba(56,73,64,0.08)] sm:p-7">
          <p className="text-xs font-bold uppercase tracking-[0.2em] text-teal-700">Broadcast</p><h2 className="mt-2 font-display text-2xl font-semibold text-stone-950">Send an update.</h2><p className="mt-1 text-sm text-stone-500">The current filters also define the broadcast audience.</p>
          <form className="mt-6 space-y-5" onSubmit={sendBroadcast}><div className="grid gap-3 sm:grid-cols-4"><label className="field-label">Send to<select className="field-input" name="role" value={broadcastRole} onChange={(event) => setBroadcastRole(event.target.value)}><option value="all">Everyone</option><option value="collector">Collectors</option><option value="giver">Givers</option></select></label><label className="field-label">Year<select className="field-input" name="year" value={filters.year} onChange={updateFilter}><option value="">All years</option>{[1, 2, 3, 4].map((year) => <option key={year} value={year}>{year}</option>)}</select></label><label className="field-label">Branch<select className="field-input" name="branch" value={filters.branch} onChange={updateFilter}><option value="">All branches</option><option value="IT">IT</option><option value="ECE">ECE</option></select></label><label className="field-label">Gender<select className="field-input" name="gender" value={filters.gender} onChange={updateFilter}><option value="">All genders</option><option value="M">M</option><option value="F">F</option></select></label></div><label className="field-label">Message<textarea className="field-input min-h-32 resize-y" value={broadcastMessage} onChange={(event) => setBroadcastMessage(event.target.value)} placeholder="Write an update for the selected audience..." required /></label><button className="primary-button sm:max-w-xs" type="submit" disabled={broadcasting}>{broadcasting ? 'Sending...' : 'Send Broadcast'}</button></form>
        </section>
      </div>
      {(error || message) && <div className="mx-auto mt-6 max-w-6xl">{error && <p className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>}{message && <p className="rounded-xl bg-teal-50 px-4 py-3 text-sm text-teal-800">{message}</p>}</div>}
    </main>
  )
}
