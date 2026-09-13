# Chanda Tracker

A web application built for the **Telugu Community of IIIT Allahabad (IIITA)** to replace messy Excel sheets with a clean, transparent, and secure way of collecting festival contributions (Chanda) for **Vinayaka Chavithi** and **Ugadi** celebrations.

---

## Features

Chanda Tracker digitizes the whole flow with three role-based experiences:

| Role | What they do |
|---|---|
| **Giver** (student) | Logs in, sees their assigned collector details + PhonePe QR, pays, and uploads the payment screenshot + transaction reference |
| **Collector** (per year/branch/gender) | Sees only their assigned givers submissions, verifies or rejects each payment, and manages their own UPI/QR profile |
| **Admin** (event lead) | Views year/branch/gender-wise collection stats and sends broadcast messages to Everyone / Collectors / Givers with filters |

**Security features:**
- Signup/login restricted to `@iiita.ac.in` institute emails + roll numbers
- Email verification via 6-digit OTP (Brevo email; 10-min expiry, max 5 attempts)
- Passwords stored as bcrypt hashes; JWT (7-day) authentication
- Google OAuth signup/login support (IIITA accounts only)
- Admin accounts use email signup only (not Google) for security

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 19, Vite, React Router, Tailwind CSS 4, Axios |
| Backend | Python 3.12, FastAPI, Uvicorn, SQLAlchemy 2 (async), Pydantic |
| Database | PostgreSQL (Supabase) via asyncpg |
| Auth | JWT (python-jose), bcrypt (passlib), Google OAuth |
| File storage | Cloudflare R2 (S3-compatible, boto3) with local fallback |
| Email | Brevo SMTP API (OTP, password reset, broadcasts) |

---

## Running Locally

### Prerequisites
- Python 3.11+ and Node.js 18+
- A Supabase project (free tier works)
- (Optional) Google OAuth credentials for Google signup/login

### 1. Clone and configure
```bash
git clone <your-repo-url>
cd Chanda Tracker
Copy-Item .env.example .env
```

### 2. Backend setup
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```
API live at http://127.0.0.1:8000 (docs at /docs)

### 3. Frontend setup
```bash
cd frontend
npm install
npm run dev
```
App runs at http://localhost:5173

### 4. Google OAuth Setup (Optional)
1. Go to Google Cloud Console
2. Create OAuth 2.0 Client ID credentials
3. Add authorized JavaScript origins: http://localhost:5173
4. Copy Client ID to backend/.env and frontend/.env

### 5. Create accounts
1. Go to /signup
2. Register as Admin, Collector, or Giver
3. Verify OTP and log in

---

## Troubleshooting

**Google Signup Invalid Google credential**
- Clock skew: Backend tolerates up to 5 seconds of clock difference
- Token expired: Click signup button promptly after Google login
- Client ID mismatch: Ensure GOOGLE_CLIENT_ID matches in both .env files

**Environment Variables Not Loading**
- Ensure .env files have no spaces around the = sign
- Restart backend after changing .env files

---

## Recent Bug Fixes

- Fixed Google auth clock skew error (added 5-second tolerance)
- Added missing google_sub column to database
- Added Admin role to signup dropdown
- Made year/branch optional for admin accounts
- Fixed .env file format (removed spaces around values)

---

Built with love by the Telugu Community, IIIT Allahabad.