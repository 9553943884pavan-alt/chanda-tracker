import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import api from '../api'
import { useAuth } from '../context/useAuth'
import { useToast } from '../context/ToastContext'
import Announcements from './Announcements'

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

export default function CollectorDashboard() {
  const { logout } = useAuth()
  const { showToast } = useToast()
  const [payments, setPayments] = useState(null)
  const [verificationId, setVerificationId] = useState(null)
  const [profile, setProfile] = useState({ upi_id: '', phone: '', qr_image_url: null, qr_image: null })
  const [savingProfile, setSavingProfile] = useState(false)

  async function loadPayments() {
    try {
      const { data } = await api.get('/collector/my-payments')
      setPayments(data)
    } catch (requestError) {
      setPayments([])
      showToast(errorMessage(requestError, 'Unable to load payments.'), 'error')
    }
  }

  async function loadProfile() {
    try {
      const { data } = await api.get('/collector/profile')
      setProfile({
        upi_id: data.upi_id || '',
        phone: data.phone || '',
        qr_image_url: data.qr_image_url || null,
        qr_image: null,
      })
    } catch (requestError) {
      console.error('Failed to load profile:', requestError)
    }
  }

  useEffect(() => {
    loadPayments()
    loadProfile()
  }, [])

  function updateProfile(event) {
    const { name, value, files } = event.target
    setProfile((current) => ({ ...current, [name]: files ? files[0] : value }))
  }

  async function saveProfile(event) {
    event.preventDefault()

    if (!profile.qr_image && !profile.qr_image_url) {
      showToast('Choose a QR image before saving your profile.', 'error')
      return
    }

    setSavingProfile(true)
    const formData = new FormData()
    if (profile.upi_id) formData.append('upi_id', profile.upi_id)
    if (profile.phone) formData.append('phone', profile.phone)
    if (profile.qr_image) formData.append('qr_image', profile.qr_image)

    try {
      const { data } = await api.post('/collector/profile', formData)
      showToast('Collector profile and QR code saved.')
      setProfile((current) => ({
        ...current,
        qr_image_url: data.qr_image_url || current.qr_image_url,
        qr_image: null,
      }))
    } catch (requestError) {
      showToast(errorMessage(requestError, 'Unable to save collector profile.'), 'error')
    } finally {
      setSavingProfile(false)
    }
  }

  async function verifyPayment(paymentId, status) {
    setVerificationId(paymentId)
    try {
      await api.patch(`/collector/payments/${paymentId}/verify`, { status })
      await loadPayments()
    } catch (requestError) {
      showToast(errorMessage(requestError, 'Unable to update payment status.'), 'error')
    } finally {
      setVerificationId(null)
    }
  }

  return (
    <main className="min-h-screen px-5 py-6 sm:px-10">
      <nav className="mx-auto flex max-w-6xl items-center justify-between border-b border-stone-200 pb-5">
        <Link to="/collector-dashboard" className="font-display text-xl font-semibold tracking-tight text-stone-950">chanda<span className="text-teal-700">.</span></Link>
        <button type="button" onClick={logout} className="text-sm font-semibold text-stone-500 transition hover:text-stone-950">Sign out</button>
      </nav>
      <header className="mx-auto max-w-6xl pb-8 pt-12">
        <p className="text-xs font-bold uppercase tracking-[0.24em] text-teal-700">Collector workspace</p>
        <h1 className="mt-3 font-display text-5xl font-semibold tracking-tight text-stone-950">Payment verification.</h1>
        <p className="mt-4 max-w-xl text-lg leading-8 text-stone-500">Review incoming contributions and keep your collection details current.</p>
      </header>
      <Announcements />
      <div className="mx-auto grid max-w-6xl gap-8 lg:grid-cols-[1fr_360px]">
        <section className="min-w-0 rounded-2xl border border-stone-200 bg-[#fffdf8]/85 p-5 shadow-[0_18px_50px_rgba(56,73,64,0.08)] sm:p-7">
          <div className="mb-6 flex items-center justify-between gap-4">
            <div><h2 className="font-display text-2xl font-semibold text-stone-950">Incoming payments</h2><p className="mt-1 text-sm text-stone-500">Verify each contribution when you have checked the proof.</p></div>
            <button type="button" onClick={loadPayments} className="rounded-lg border border-stone-300 px-3 py-2 text-xs font-bold text-stone-600 hover:border-teal-700 hover:text-teal-800">Refresh</button>
          </div>
          {payments === null ? <p className="py-10 text-center text-sm text-stone-500">Loading payments...</p> : payments.length === 0 ? <p className="py-10 text-center text-sm text-stone-500">No payments yet.</p> : (
            <div className="overflow-x-auto"><table className="w-full min-w-[720px] text-left text-sm"><thead className="border-b border-stone-200 text-xs uppercase tracking-wider text-stone-500"><tr><th className="pb-3 pr-4">Giver</th><th className="pb-3 pr-4">Amount</th><th className="pb-3 pr-4">Reference</th><th className="pb-3 pr-4">Proof</th><th className="pb-3 pr-4">Status</th><th className="pb-3">Action</th></tr></thead><tbody className="divide-y divide-stone-100">{payments.map((payment) => <tr key={payment.id}><td className="py-4 pr-4"><strong className="block text-stone-800">{payment.giver_full_name}</strong><span className="text-xs text-stone-500">{payment.giver_roll_no}</span></td><td className="py-4 pr-4 font-bold text-stone-800">₹{Number(payment.amount).toFixed(2)}</td><td className="py-4 pr-4 font-mono text-xs text-stone-600">{payment.transaction_ref}</td><td className="py-4 pr-4"><a className="font-bold text-teal-800 hover:text-teal-950" href={payment.screenshot_url} target="_blank" rel="noreferrer">View Screenshot</a></td><td className="py-4 pr-4"><StatusBadge status={payment.status} /></td><td className="py-4">{payment.status === 'pending' ? <div className="flex gap-2"><button type="button" disabled={verificationId === payment.id} onClick={() => verifyPayment(payment.id, 'verified')} className="rounded-lg bg-emerald-700 px-3 py-2 text-xs font-bold text-white hover:bg-emerald-800 disabled:opacity-50">Verify</button><button type="button" disabled={verificationId === payment.id} onClick={() => verifyPayment(payment.id, 'rejected')} className="rounded-lg border border-red-200 px-3 py-2 text-xs font-bold text-red-700 hover:bg-red-50 disabled:opacity-50">Reject</button></div> : <span className="text-xs text-stone-400">Completed</span>}</td></tr>)}</tbody></table></div>
          )}
        </section>
        <section className="h-fit rounded-2xl border border-stone-200 bg-[#fffdf8]/85 p-5 shadow-[0_18px_50px_rgba(56,73,64,0.08)] sm:p-7">
          <p className="text-xs font-bold uppercase tracking-[0.2em] text-teal-700">Profile</p>
          <h2 className="mt-2 font-display text-2xl font-semibold text-stone-950">Your QR details</h2>
          {profile.qr_image_url && (
            <div className="mt-4 mb-2">
              <p className="text-xs font-bold uppercase tracking-wider text-stone-400 mb-2">Active QR Code</p>
              <img className="aspect-square w-full rounded-xl border border-stone-200 object-contain bg-white p-2" src={profile.qr_image_url} alt="Active QR code" />
            </div>
          )}
          <form className="mt-4 space-y-5" onSubmit={saveProfile}>
            <label className="field-label">UPI ID<input className="field-input" name="upi_id" value={profile.upi_id} onChange={updateProfile} placeholder="name@upi" /></label>
            <label className="field-label">Phone<input className="field-input" name="phone" value={profile.phone} onChange={updateProfile} placeholder="9876543210" /></label>
            <label className="field-label">
              {profile.qr_image_url ? 'Replace QR image (Optional)' : 'QR image'}
              <input className="field-input file:mr-3 file:rounded-md file:border-0 file:bg-teal-50 file:px-2 file:py-1 file:text-xs file:font-bold" name="qr_image" type="file" accept="image/*" onChange={updateProfile} required={!profile.qr_image_url} />
            </label>
            <button className="primary-button" type="submit" disabled={savingProfile}>{savingProfile ? 'Saving...' : 'Save QR profile'}</button>
          </form>
        </section>
      </div>
    </main>
  )
}

