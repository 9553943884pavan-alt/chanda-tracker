# Chanda Tracker — Project Report

> Context document describing the website design, features, and technical implementation.

## 1. Project Overview

**Chanda Tracker** is a full-stack web application built for the **Telugu Community of IIIT Allahabad (IIITA)**. It replaces the manual Excel-sheet process of collecting festival contributions (Chanda) for two major festivals — **Vinayaka Chavithi** and **Ugadi** — with a transparent, role-based digital platform.

**Core domain model:** Students of years 1–4 belong to groups based on **year, branch (IT/ECE), and gender**. Each group has one assigned money **Collector**. Every student (money **Giver**) pays their assigned collector via PhonePe QR, uploads proof, and the collector verifies it. An **Admin** (event lead) oversees everything and can broadcast messages.

## 2. User Roles & Features

### Giver (student paying money)
- Signs up with name, `@iiita.ac.in` email, roll number, role, year, branch, gender
- Email verified via 6-digit OTP, then sets a password (min 8 chars, letters + numbers/symbols)
- Dashboard shows **assigned collector** (auto-resolved by year/branch/gender matching), their UPI ID, phone, and **PhonePe QR code** (signed URL image)
- Submits payment: amount + transaction reference (UTR) + screenshot upload
- Sees **payment history table** with live status: pending / verified / rejected, collector notes, and a success banner when verified
- Sees **Announcements** panel (broadcasts targeted to their role/year/branch/gender)

### Collector (money collector per group)
- Same signup/OTP flow (boys: branch-specific; girls: all-branch per year)
- Uploads/manages **UPI ID, phone, and QR code** profile
- Sees **only their assigned givers' payments**: giver name/roll, amount, transaction ref, screenshot link (presigned URL), status
- Can **Verify or Reject** each pending payment (optionally with notes)
- Status badges: amber = pending, green = verified, red = rejected
- Sees Announcements panel too

### Admin (event lead)
- Special signup (no year/branch required)
- Dashboard with **aggregate stats**: total collected, pending, verified/rejected counts, collector/giver counts
- **Payments explorer** filterable by year / branch / gender, with screenshot viewing
- **Broadcast messaging** (WhatsApp-group style) with filters:
  - Send to: **Everyone / Collectors only / Givers only**
  - Year (1–4 or all), Branch (IT/ECE/all), Gender (M/F/all)
  - Delivered via Brevo email AND shown in the in-app Announcements feed
- Admin sees all broadcasts; students only see ones matching their profile

### Authentication (all roles)
- **Signup:** details → OTP to email (Brevo) → verify → set password → account created
- **Login:** email + password → JWT bearer token (HS256, 7-day expiry)
- **Forgot Password:** email → OTP → new password + confirm password (validated, must match)
- OTP rules: 6-digit, hashed in DB, 10-minute expiry, max 5 wrong attempts
- Signup restricted to `@iiita.ac.in` emails; email/roll_no unique


## 3. UI/UX Design

- **Design language:** Warm, editorial "chanda." brand — cream/off-white card surfaces (`#fffdf8`), stone-gray text, **teal accent** (teal-700/800), large rounded cards, soft shadows, uppercase letter-spaced section labels, display headings
- **Layout:** Centered auth cards (max-w-md), dashboard grids (main content + side panel), full-width announcement panel, responsive to mobile (Tailwind breakpoints)
- **Pages:** Login (with Forgot password link), Signup (2-step: details → OTP+password), ForgotPassword (2-step: email → OTP + new/confirm password), CollectorDashboard, GiverDashboard, AdminDashboard
- **Route protection:** `ProtectedRoute` redirects unauthenticated users to `/login` and role-mismatched users to their own dashboard
- **Auth state:** React Context; JWT in localStorage, decoded client-side for role + expiry; Axios interceptor attaches `Authorization: Bearer` header

## 4. Technical Implementation

### Stack
| Layer | Technology |
|---|---|
| Frontend | React 19 + Vite, React Router, Tailwind CSS 4, Axios |
| Backend | Python 3.12, FastAPI (async), Uvicorn, Pydantic |
| ORM/DB | SQLAlchemy 2 async + asyncpg → PostgreSQL on Supabase |
| Auth | python-jose (JWT HS256), passlib + bcrypt |
| Files | Cloudflare R2 (S3 API via boto3), presigned URLs, local `uploads/` fallback |
| Email | Brevo HTTP API (OTP, password reset, broadcasts) |

### Backend structure (`backend/`)
- `main.py` — FastAPI app, CORS, static `/uploads` mount, lifespan DB health check + seeds 12 collector groups (4 years × IT-M, ECE-M, all-branch-F)
- `database.py` — async engine/session, `gen_random_uuid()` PKs
- `models.py` — `User` (role check: admin/collector/giver; year 1–4; branch IT/ECE; gender M/F), `CollectorGroup`, `CollectorProfile` (UPI, QR key, phone), `OTPCode` (purpose signup/reset, hashed code, attempts), `Payment` (amount, unique transaction_ref, status pending/verified/rejected, screenshot_key, verified_by/at, notes), `Broadcast` (filter_role all/collector/giver, filter_year/branch/gender, message)
- `routers/auth.py` — signup/verify-otp/login/forgot-password/reset-password; pending signups in memory; OTPs emailed via Brevo, printed to console in dev
- `routers/giver.py` — collector assignment resolution (group match → fallback direct user match), `POST /submit-payment` (amount, ref pattern, image type, ≤10MB), `GET /my-payments`
- `routers/collector.py` — profile upsert with QR upload (≤5MB), `GET /my-payments`, `PATCH /payments/{id}/verify` (ownership-enforced)
- `routers/admin.py` — stats aggregation, filtered payments list with presigned screenshot URLs, broadcast creation + Brevo delivery
- `routers/broadcasts.py` — `GET /broadcasts` feed; filters: role (all/matching), year, branch (users without a branch only get unbranch-targeted broadcasts), gender; null filter = wildcard; admins see all
- `storage.py` — R2 upload with local-disk fallback; presigned GET URLs (5-min expiry)
- `dependencies.py` — `get_current_user` JWT validation

### Frontend structure (`frontend/src/`)
- `api.js` — Axios instance (`VITE_API_URL` with localhost fallback) + token interceptor
- `context/` — AuthProvider / AuthContext / useAuth (login, logout, role, isAuthenticated)
- `pages/` — Login, Signup, ForgotPassword, CollectorDashboard, GiverDashboard, AdminDashboard, Announcements (shared broadcast feed)
- Config via `frontend/.env` (`VITE_API_URL`)

### Security measures
- Bcrypt password hashing (never plaintext, irreversible)
- OTPs bcrypt-hashed, expiring, attempt-limited
- JWT signed with server secret from `.env`; role re-verified server-side per request
- Collector verification endpoint enforces ownership
- Transaction refs unique at DB level (prevents duplicate claims)
- Secrets in `.env` (gitignored); `.env.example` template provided

### Data flow (payment lifecycle)
Giver login → collector auto-resolved → QR shown → pay on PhonePe → submit proof (R2 upload + `payments` row, pending) → collector reviews screenshot → verify/reject → status reflects in giver dashboard → admin monitors aggregates and broadcasts updates.

## 5. Deployment Topology (current)

- Frontend: Vite dev server / static build (`npm run build` → `dist/`)
- Backend: Uvicorn on `http://127.0.0.1:8000`
- DB: Supabase Postgres (connection pooler, port 6543, SSL required)
- Files: Cloudflare R2 bucket `chanda-tracker-uploads`
- Email: Brevo verified sender `iec2025049@iiita.ac.in`
