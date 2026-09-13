import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { GoogleLogin } from '@react-oauth/google'
import api from '../api'
import { useAuth } from '../context/useAuth'
import { useToast } from '../context/ToastContext'

// Step 1 details only — no email here anymore (email is collected on the "Sign up with Email" path).
const initialForm = {
  full_name: '',
  roll_no: '',
  role: 'giver',
  year: '',
  branch: '',
  gender: '',
}

function getErrorMessage(error) {
  const detail = error.response?.data?.detail
  if (Array.isArray(detail)) return detail.map((item) => item.msg).join(', ')
  return detail || 'Unable to complete signup. Check your details and try again.'
}

// Step 1 is valid only when every required field is filled.
// Admin accounts don't require year/branch (they're not students).
function isStep1Valid(form) {
  const baseValid = (
    form.full_name.trim() !== '' &&
    form.roll_no.trim() !== '' &&
    form.role !== '' &&
    form.gender !== ''
  )
  if (!baseValid) return false
  // Admin only needs full_name, roll_no, role, gender
  if (form.role === 'admin') return true
  // Students need year and branch (if male)
  return form.year !== '' && (form.gender !== 'M' || form.branch !== '')
}

export default function Signup() {
  const navigate = useNavigate()
  const { login } = useAuth()
  const { showToast } = useToast()

  // Step 1 data — carried forward regardless of which signup path is chosen.
  const [form, setForm] = useState(initialForm)

  // 'details' -> basic info form
  // 'choice'  -> pick Google or Email
  // 'email'   -> enter email, then OTP verification
  const [step, setStep] = useState('details')

  // Email-path state (Path A).
  const [email, setEmail] = useState('')
  const [otp, setOtp] = useState('')
  const [password, setPassword] = useState('')

  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  function updateField(event) {
    setForm((current) => ({ ...current, [event.target.name]: event.target.value }))
  }

  function proceedToChoice() {
    if (!isStep1Valid(form)) {
      setError('Please fill in all required fields before continuing.')
      return
    }
    setError('')
    // Admin accounts must use email signup (Google signup doesn't support admin role)
    if (form.role === 'admin') {
      setStep('email')
    } else {
      setStep('choice')
    }
  }

  // ---- Path B: Sign up with Google ----
  async function handleGoogleSignup(credentialResponse) {
    setError('')
    setLoading(true)
    try {
      const { data } = await api.post('/auth/google/signup', {
        credential: credentialResponse.credential,
        full_name: form.full_name.trim(),
        roll_no: form.roll_no.trim(),
        role: form.role,
        year: Number(form.year),
        branch: form.branch || null,
        gender: form.gender || null,
      })
      const payload = login(data.access_token)
      const destination = {
        collector: '/collector-dashboard',
        giver: '/giver-dashboard',
        admin: '/admin-dashboard',
      }[payload.role]
      if (!destination) throw new Error('Unknown account role')
      navigate(destination, { replace: true })
    } catch (requestError) {
      setError(getErrorMessage(requestError))
    } finally {
      setLoading(false)
    }
  }

  function handleGoogleError() {
    setError('Google sign-in was cancelled or failed. Please try again.')
  }

  // ---- Path A: Sign up with Email ----
  function chooseEmail() {
    setError('')
    setStep('email')
  }

  async function requestOtp(event) {
    event.preventDefault()
    setError('')
    setLoading(true)
    try {
      await api.post('/auth/signup', {
        full_name: form.full_name.trim(),
        email: email.trim().toLowerCase(),
        roll_no: form.roll_no.trim(),
        role: form.role,
        year: Number(form.year),
        branch: form.branch || null,
        gender: form.gender || null,
      })
      showToast('Verification code sent. Check your institute email.', 'success')
      setStep('verify')
    } catch (requestError) {
      setError(getErrorMessage(requestError))
    } finally {
      setLoading(false)
    }
  }

  async function verifyAccount(event) {
    event.preventDefault()
    setError('')
    setLoading(true)
    try {
      await api.post('/auth/verify-otp', { email: email.trim().toLowerCase(), otp, password })
      navigate('/login', { replace: true, state: { message: 'Account created. You can now sign in.' } })
    } catch (requestError) {
      setError(getErrorMessage(requestError))
    } finally {
      setLoading(false)
    }
  }

  const roleLabel = step === 'details' ? 'Join the circle' : step === 'choice' ? 'Choose how to sign up' : 'Almost there'
  const heading = step === 'details' ? 'Create your account.' : step === 'choice' ? 'Pick your sign-up method.' : step === 'email' ? 'Enter your institute email.' : 'Verify your email.'
  const stepIndicator = step === 'details' ? '1 / 2' : step === 'choice' ? '2 / 2' : '2 / 2'

  return (
    <main className="grid min-h-screen place-items-center px-5 py-10">
      <section className="w-full max-w-2xl rounded-[2rem] border border-stone-200/80 bg-[#fffdf8]/90 p-7 shadow-[0_24px_80px_rgba(56,73,64,0.12)] backdrop-blur sm:p-10">
        <div className="mb-9 flex items-start justify-between gap-5">
          <div>
            <Link to="/login" className="font-display text-2xl font-semibold text-stone-950">chanda<span className="text-teal-700">.</span></Link>
            <p className="mt-8 text-xs font-bold uppercase tracking-[0.24em] text-teal-700">{roleLabel}</p>
            <h1 className="mt-3 font-display text-4xl font-semibold tracking-tight text-stone-950">{heading}</h1>
          </div>
          <span className="rounded-full bg-teal-50 px-3 py-1 text-xs font-bold text-teal-800">{stepIndicator}</span>
        </div>

        {/* Step 1 — basic details (same for everyone) */}
        {step === 'details' && (
          <form className="grid gap-5 sm:grid-cols-2" onSubmit={(e) => { e.preventDefault(); proceedToChoice() }}>
            <label className="field-label sm:col-span-2">Full name<input className="field-input" name="full_name" value={form.full_name} onChange={updateField} required /></label>
            <label className="field-label">Roll number<input className="field-input" name="roll_no" value={form.roll_no} onChange={updateField} required /></label>
            <label className="field-label">Role<select className="field-input" name="role" value={form.role} onChange={updateField}><option value="giver">Giver</option><option value="collector">Collector</option><option value="admin">Admin</option></select></label>
            {form.role !== 'admin' && (
              <>
                <label className="field-label">Year<select className="field-input" name="year" value={form.year} onChange={updateField}><option value="">Select year</option>{[1, 2, 3, 4].map((year) => <option key={year} value={year}>{year}</option>)}</select></label>
                <label className="field-label">Branch<select className="field-input" name="branch" value={form.branch} onChange={updateField}><option value="">Select branch</option><option value="IT">IT</option><option value="ECE">ECE</option></select></label>
              </>
            )}
            <label className="field-label">Gender<select className="field-input" name="gender" value={form.gender} onChange={updateField}><option value="">Select gender</option><option value="M">M</option><option value="F">F</option></select></label>
            {form.role === 'admin' && <p className="rounded-xl bg-teal-50 px-4 py-3 text-sm text-teal-900 sm:col-span-2">Admin accounts use email signup only (no Google signup).</p>}
            {error && <p className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700 sm:col-span-2">{error}</p>}
            <button className="primary-button sm:col-span-2" type="submit">Continue</button>
          </form>
        )}

        {/* Step 2 — choice screen */}
        {step === 'choice' && (
          <div className="space-y-4">
            <GoogleLogin
              onSuccess={handleGoogleSignup}
              onError={handleGoogleError}
              text="signup_with"
              shape="pill"
              size="large"
              width="100%"
              hosted_domain="iiita.ac.in"
            />
            <div className="flex items-center gap-4 text-stone-400">
              <span className="h-px flex-1 bg-stone-200" />
              <span className="text-xs font-bold uppercase tracking-widest">or</span>
              <span className="h-px flex-1 bg-stone-200" />
            </div>
            <button className="primary-button w-full" type="button" onClick={chooseEmail}>Sign up with Email</button>
            {error && <p className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>}
            <button className="w-full text-sm text-stone-500 hover:text-stone-800" type="button" onClick={() => { setError(''); setStep('details') }}>← Back to details</button>
          </div>
        )}

        {/* Path A — enter email */}
        {step === 'email' && (
          <form className="space-y-5" onSubmit={requestOtp}>
            <label className="field-label">Institute email<input className="field-input" name="email" type="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="you@iiita.ac.in" required /></label>
            {error && <p className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>}
            <button className="primary-button w-full" type="submit" disabled={loading}>{loading ? 'Sending code...' : 'Send verification code'}</button>
            <button className="w-full text-sm text-stone-500 hover:text-stone-800" type="button" onClick={() => { setError(''); setStep('choice') }}>← Back</button>
          </form>
        )}

        {/* Path A — verify OTP + set password */}
        {step === 'verify' && (
          <form className="space-y-5" onSubmit={verifyAccount}>
            <p className="rounded-xl bg-teal-50 px-4 py-3 text-sm leading-6 text-teal-900">A six-digit code was sent to <strong>{email.trim().toLowerCase()}</strong>.</p>
            <label className="field-label">Verification code<input className="field-input tracking-[0.35em]" inputMode="numeric" maxLength="6" value={otp} onChange={(event) => setOtp(event.target.value.replace(/\D/g, ''))} required /></label>
            <label className="field-label">
              Create password
              <input className="field-input" type="password" minLength="8" value={password} onChange={(event) => setPassword(event.target.value)} placeholder="Minimum 8 characters (letters & numbers)" required />
              <span className="mt-1 text-xs text-stone-500 font-normal">Must be at least 8 characters with a mix of letters and numbers/symbols.</span>
            </label>
            {error && <p className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>}
            <button className="primary-button w-full" type="submit" disabled={loading}>{loading ? 'Creating account...' : 'Verify and create account'}</button>
            <button className="w-full text-sm text-stone-500 hover:text-stone-800" type="button" onClick={() => { setError(''); setOtp(''); setPassword(''); setStep('email') }}>← Back</button>
          </form>
        )}

        <p className="mt-7 text-center text-sm text-stone-500">Already registered? <Link className="font-bold text-teal-800 hover:text-teal-950" to="/login">Sign in</Link></p>
      </section>
    </main>
  )
}
