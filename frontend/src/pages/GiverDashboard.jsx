import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import api from '../api'
import { useAuth } from '../context/useAuth'
import Announcements from './Announcements'

function errorMessage(error, fallback) {
  return error.response?.data?.detail || fallback
}

// UPI UTR: exactly 12 digits | PhonePe Transaction ID: T followed by 20-23 digits
const UTR_PATTERN = /^\d{12}$/
const PHONEPE_TXN_PATTERN = /^T\d{20,23}$/

function isValidTransactionRef(ref) {
  const value = ref.trim()
  return UTR_PATTERN.test(value) || PHONEPE_TXN_PATTERN.test(value)
}

export default function GiverDashboard() {
  const { logout } = useAuth()
  const [collector, setCollector] = useState(null)
  const [payments, setPayments] = useState(null)
  const [loading, setLoading] = useState(true)
  const [form, setForm] = useState({ amount: '', transaction_ref: '', screenshot: null })
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  function statusStyles(status) {
    const styles = {
      pending: 'bg-amber-50 text-amber-800 ring-amber-200',
      verified: 'bg-emerald-50 text-emerald-800 ring-emerald-200',
      rejected: 'bg-red-50 text-red-800 ring-red-200',
    }
    return `inline-flex rounded-full px-3 py-1 text-xs font-bold capitalize ring-1 ${styles[status] || 'bg-stone-100 text-stone-700 ring-stone-200'}`
  }

  async function loadPayments() {
    try {
      const { data } = await api.get('/giver/my-payments')
      setPayments(data)
    } catch (requestError) {
      setPayments([])
      setError(errorMessage(requestError, 'Unable to load your payment history.'))
    }
  }

  useEffect(() => {
    async function loadCollector() {
      try {
        const { data } = await api.get('/giver/my-collector')
        setCollector(data)
      } catch (requestError) {
        setError(errorMessage(requestError, 'Unable to load your assigned collector.'))
      } finally {
        setLoading(false)
      }
    }
    loadCollector()
    loadPayments()
  }, [])

  function updateForm(event) {
    const { name, value, files } = event.target
    setForm((current) => ({ ...current, [name]: files ? files[0] : value }))
  }

  async function submitPayment(event) {
    event.preventDefault()
    setSubmitting(true)
    setError('')
    setMessage('')
    if (!form.screenshot) {
      setError('Choose a payment screenshot before submitting.')
      setSubmitting(false)
      return
    }
    if (!isValidTransactionRef(form.transaction_ref)) {
      setError('Enter a valid 12-digit UTR number or a PhonePe Transaction ID starting with T.')
      setSubmitting(false)
      return
    }
    const formData = new FormData()
    formData.append('amount', form.amount)
    formData.append('transaction_ref', form.transaction_ref.trim())
    formData.append('screenshot', form.screenshot)
    try {
      const { data } = await api.post('/giver/submit-payment', formData)
      setMessage(data.message || 'Payment submitted for verification.')
      setForm({ amount: '', transaction_ref: '', screenshot: null })
      event.target.reset()
      await loadPayments()
    } catch (requestError) {
      setError(errorMessage(requestError, 'Unable to submit payment.'))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <main className="min-h-screen px-5 py-6 sm:px-10">
      <nav className="mx-auto flex max-w-6xl items-center justify-between border-b border-stone-200 pb-5"><Link to="/giver-dashboard" className="font-display text-xl font-semibold tracking-tight text-stone-950">chanda<span className="text-teal-700">.</span></Link><button type="button" onClick={logout} className="text-sm font-semibold text-stone-500 transition hover:text-stone-950">Sign out</button></nav>
      <header className="mx-auto max-w-6xl pb-8 pt-12"><p className="text-xs font-bold uppercase tracking-[0.24em] text-teal-700">Giver workspace</p><h1 className="mt-3 font-display text-5xl font-semibold tracking-tight text-stone-950">Make a contribution.</h1><p className="mt-4 max-w-xl text-lg leading-8 text-stone-500">Find your assigned collector and submit your payment proof in one place.</p></header>
      <div className="mx-auto grid max-w-6xl gap-8 lg:grid-cols-[360px_1fr]">
        <section className="h-fit rounded-2xl border border-stone-200 bg-[#fffdf8]/85 p-5 shadow-[0_18px_50px_rgba(56,73,64,0.08)] sm:p-7">
          <p className="text-xs font-bold uppercase tracking-[0.2em] text-teal-700">Your assignment</p>
          <h2 className="mt-2 font-display text-2xl font-semibold text-stone-950">Collector details</h2>
          {loading ? (
            <p className="mt-6 text-sm text-stone-500">Loading collector...</p>
          ) : collector ? (
            <div className="mt-6 space-y-4">
              <div>
                <p className="text-xs font-bold uppercase tracking-wider text-stone-400">Name</p>
                <p className="mt-1 text-lg font-bold text-stone-800">{collector.full_name}</p>
              </div>
              {collector.upi_id && (
                <div>
                  <p className="text-xs font-bold uppercase tracking-wider text-stone-400">UPI ID</p>
                  <p className="mt-1 font-mono text-sm text-teal-800 font-semibold">{collector.upi_id}</p>
                </div>
              )}
              {collector.phone && (
                <div>
                  <p className="text-xs font-bold uppercase tracking-wider text-stone-400">Phone</p>
                  <p className="mt-1 text-stone-700">{collector.phone}</p>
                </div>
              )}
              {collector.qr_image_url ? (
                <div className="pt-2">
                  <p className="text-xs font-bold uppercase tracking-wider text-stone-400 mb-2">Scan & Pay QR</p>
                  <img className="aspect-square w-full rounded-xl border border-stone-200 object-contain bg-white p-2" src={collector.qr_image_url} alt={`QR code for ${collector.full_name}`} />
                </div>
              ) : (
                <div className="rounded-xl bg-amber-50 p-4 text-xs leading-5 text-amber-800 border border-amber-200">
                  {collector.message || 'Your assigned collector has not uploaded a payment QR code yet.'}
                </div>
              )}
            </div>
          ) : null}
        </section>
        <section className="rounded-2xl border border-stone-200 bg-[#fffdf8]/85 p-5 shadow-[0_18px_50px_rgba(56,73,64,0.08)] sm:p-7">
          <p className="text-xs font-bold uppercase tracking-[0.2em] text-teal-700">Payment proof</p>
          <h2 className="mt-2 font-display text-2xl font-semibold text-stone-950">Submit a payment</h2>
          <form className="mt-6 max-w-xl space-y-5" onSubmit={submitPayment}>
            <label className="field-label">Amount (₹)<input className="field-input" name="amount" type="number" min="0.01" step="0.01" value={form.amount} onChange={updateForm} placeholder="500.00" required /></label>
            <label className="field-label">
              Transaction reference (UTR / Txn ID)
              <input className="field-input" name="transaction_ref" value={form.transaction_ref} onChange={updateForm} placeholder="139709650010 or T2609110049222606913740" required />
              <span className="mt-1 text-xs text-stone-500 font-normal">Enter your 12-digit UTR number or PhonePe Transaction ID</span>
            </label>
            <label className="field-label">Payment screenshot<input className="field-input file:mr-3 file:rounded-md file:border-0 file:bg-teal-50 file:px-2 file:py-1 file:text-xs file:font-bold" name="screenshot" type="file" accept="image/*" onChange={updateForm} required /></label>
            <button className="primary-button" type="submit" disabled={submitting}>{submitting ? 'Submitting...' : 'Submit payment proof'}</button>
          </form>
        </section>
      </div>
      <Announcements />
      <section className="mx-auto mt-8 max-w-6xl rounded-2xl border border-stone-200 bg-[#fffdf8]/85 p-5 shadow-[0_18px_50px_rgba(56,73,64,0.08)] sm:p-7">
        <p className="text-xs font-bold uppercase tracking-[0.2em] text-teal-700">Payment history</p>
        <h2 className="mt-2 font-display text-2xl font-semibold text-stone-950">Your submitted payments</h2>
        {payments === null ? (
          <p className="mt-6 text-sm text-stone-500">Loading payments...</p>
        ) : payments.length === 0 ? (
          <p className="mt-6 text-sm text-stone-500">You have not submitted any payments yet.</p>
        ) : (
          <div className="mt-6 overflow-x-auto">
            <table className="w-full min-w-[640px] text-left text-sm">
              <thead className="border-b border-stone-200 text-xs uppercase tracking-wider text-stone-500">
                <tr><th className="pb-3 pr-4">Collector</th><th className="pb-3 pr-4">Amount</th><th className="pb-3 pr-4">Reference</th><th className="pb-3 pr-4">Submitted</th><th className="pb-3 pr-4">Status</th><th className="pb-3">Notes</th></tr>
              </thead>
              <tbody className="divide-y divide-stone-100">
                {payments.map((payment) => (
                  <tr key={payment.id}>
                    <td className="py-4 pr-4"><strong className="block text-stone-800">{payment.collector_full_name}</strong></td>
                    <td className="py-4 pr-4 font-bold text-stone-800">₹{Number(payment.amount).toFixed(2)}</td>
                    <td className="py-4 pr-4 font-mono text-xs text-stone-600">{payment.transaction_ref}</td>
                    <td className="py-4 pr-4 text-xs text-stone-500">{payment.submitted_at ? new Date(payment.submitted_at).toLocaleString() : '—'}</td>
                    <td className="py-4 pr-4"><span className={statusStyles(payment.status)}>{payment.status}</span></td>
                    <td className="py-4 text-xs text-stone-500">{payment.notes || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {payments?.some((payment) => payment.status === 'verified') && (
          <p className="mt-5 rounded-xl bg-emerald-50 px-4 py-3 text-sm font-semibold text-emerald-800">Your payment has been verified by your collector. No further action is needed.</p>
        )}
      </section>
      {(error || message) && <div className="mx-auto mt-6 max-w-6xl">{error && <p className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>}{message && <p className="rounded-xl bg-teal-50 px-4 py-3 text-sm text-teal-800">{message}</p>}</div>}
    </main>
  )
}

