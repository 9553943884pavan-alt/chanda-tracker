# 🪙 Chanda Tracker

A web application built for the **Telugu Community of IIIT Allahabad (IIITA)** to replace messy Excel sheets with a clean, transparent, and secure way of collecting festival contributions (Chanda) for **Vinayaka Chavithi** and **Ugadi** celebrations.

---

## 📌 The Problem

Every year, the community collects money from students of all 4 years for two big festivals. The entire process was maintained manually in **Excel sheets** by seniors, which caused:

- Messy, hard-to-maintain records spread across multiple files
- No transparency — students could not confirm their payment was recorded
- Manual verification of PhonePe screenshots and transaction IDs
- No easy way for event leads to message collectors or contributors
- Sensitive records (names, amounts) floating around in shared files

## ✅ The Solution

Chanda Tracker digitizes the whole flow with three role-based experiences:

| Role | What they do |
|---|---|
| **Giver** (student) | Logs in, sees their **assigned collector's details + PhonePe QR**, pays, and uploads the payment screenshot + transaction reference |
| **Collector** (per year/branch/gender) | Sees **only their assigned givers'** submissions, verifies or rejects each payment, and manages their own UPI/QR profile |
| **Admin** (event lead) | Views year/branch/gender-wise collection stats and sends **broadcast messages** (like a WhatsApp group) to Everyone / Collectors / Givers with year, branch, and gender filters |

**Collector assignment logic (matching the community structure):**

- Year 1–4 x IT boys → 1 collector each
- Year 1–4 x ECE boys → 1 collector each
- Year 1–4 x all-branch girls → 1 collector each

**Security features:**

- Signup/login restricted to `@iiita.ac.in` institute emails + roll numbers
- Email verification via **6-digit OTP** (Brevo email; 10-min expiry, max 5 attempts)
- Passwords stored as **bcrypt hashes**; JWT (7-day) authentication
- **Forgot Password** flow: OTP → new password + confirmation, with validation rules

## 🛠️ Tech Stack & Tools

| Layer | Technology |
|---|---|
| Frontend | React 19, Vite, React Router, Tailwind CSS 4, Axios |
| Backend | Python 3.12, FastAPI, Uvicorn, SQLAlchemy 2 (async), Pydantic |
| Database | PostgreSQL (Supabase) via asyncpg |
| Auth | JWT (python-jose), bcrypt (passlib) |
| File storage | Cloudflare R2 (S3-compatible, boto3) with local fallback |
| Email | Brevo SMTP API (OTP, password reset, broadcasts) |
| Tools | Git, npm, pip / venv, Supabase dashboard, Cloudflare dashboard |

---

## 🏗️ Application Architecture

```
+---------------------+         HTTPS/JSON          +--------------------------+
|   React Frontend    |  -------------------------> |     FastAPI Backend      |
|  (Vite + Tailwind)  | <-------------------------  |  (Uvicorn, async)        |
|  Login / Signup /   |      JWT Bearer token       |                          |
|  3 Dashboards       |                             +------------+-------------+
+---------------------+                                          |
+---------------------+     presigned URLs          +------------v-------------+
|   Supabase          | <-------------------------  |  Cloudflare R2 (S3)      |
|   PostgreSQL DB     |                             |  QR codes & screenshots  |
|  users, otp_codes,  |                             |  (local uploads fallback)|
|  collector_groups,  |                             +--------------------------+
|  collector_profiles,|
|  payments,          |   +---------------------+
|  broadcasts         |   |  Brevo Email API    |  OTPs, resets, broadcast emails
+---------------------+   +---------------------+
```

**Flow of a payment:**

1. Giver logs in -> `GET /giver/my-collector` resolves their assigned collector via year/branch/gender group matching
2. Giver pays via the collector's PhonePe QR and submits amount + transaction ref + screenshot -> stored in R2 + `payments` table (pending)
3. Collector sees it in `/collector/my-payments`, checks the proof, and verifies/rejects -> `PATCH /collector/payments/{id}/verify`
4. Giver's dashboard reflects the live status; admin sees aggregated stats and can broadcast updates

---

## 📂 Folder Structure

```
Chanda Tracker/
|-- backend/                    # FastAPI (Python) REST API
|   |-- main.py                 # App entry: CORS, routers, static uploads, DB check & seeding
|   |-- database.py             # Async SQLAlchemy engine, session, collector-group seeding
|   |-- models.py               # User, CollectorGroup, CollectorProfile, OTPCode, Payment, Broadcast
|   |-- dependencies.py         # JWT auth dependency (get_current_user)
|   |-- storage.py              # R2 upload + presigned URLs (local uploads/ fallback)
|   |-- requirements.txt        # Python dependencies
|   |-- routers/
|   |   |-- auth.py             # Signup + OTP, login, forgot/reset password
|   |   |-- collector.py        # Collector profile/QR, my-payments, verify payment
|   |   |-- giver.py            # My collector, submit payment, my-payments
|   |   |-- admin.py            # Stats, filtered payments, broadcasts
|   |   +-- broadcasts.py       # Role/branch/year/gender-filtered broadcast feed
|   +-- uploads/                # Local fallback for uploaded files (gitignored)
|-- frontend/                   # React (Vite + Tailwind CSS)
|   +-- src/
|       |-- api.js              # Axios instance with JWT interceptor
|       |-- App.jsx             # Routes + protected routes
|       |-- context/            # AuthContext / AuthProvider (token & role state)
|       +-- pages/              # Login, Signup, ForgotPassword, 3 dashboards, Announcements
|-- .env                        # Backend secrets (gitignored - see .env.example)
|-- .env.example                # Template for required environment variables
+-- .gitignore
```

---

## 🚀 Running Locally

### Prerequisites

- Python 3.11+ and Node.js 18+
- A Supabase project (free tier works) — get the connection string
- (Optional) Cloudflare R2 bucket and Brevo API key — without them the app still runs using local file storage and console-logged OTPs

### 1. Clone the repository

```bash
git clone <your-repo-url>
cd "Chanda Tracker"
```

### 2. Configure environment variables

```bash
# Windows (PowerShell)
Copy-Item .env.example .env

# Linux / macOS
cp .env.example .env
```

Open `.env` and fill in your `DATABASE_URL`, `JWT_SECRET` (generate with `python -c "import secrets; print(secrets.token_hex(32))"`), and optionally the R2 / Brevo keys.

### 3. Backend setup

```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate
# Linux / macOS
source .venv/bin/activate

pip install -r requirements.txt
uvicorn main:app --reload
```

API is now live at **http://127.0.0.1:8000** (interactive docs at `/docs`). On startup it connects to the DB and auto-seeds the 12 collector groups.

### 4. Frontend setup (new terminal)

```bash
cd frontend
npm install
npm run dev
```

App runs at **http://localhost:5173**. If your backend runs elsewhere, set `VITE_API_URL` in `frontend/.env`.

### 5. Create accounts

1. Go to **/signup** → register as **Admin** (skip year/branch) → verify the OTP → log in to the admin dashboard
2. Register **Collector** and **Giver** accounts the same way
3. Collector: upload UPI ID + QR in their dashboard → givers start seeing the QR and can pay

---

## ⚠️ Known Limitations

- OTP codes are printed to the backend console only when DEBUG=true is set (local development). Leave DEBUG unset in production (e.g. Render) — OTP codes never appear in logs
- Pending signups are stored in the database (otp_codes.payload JSON column), so unverified signups survive backend restarts on platforms like Render
- Expired OTP codes are not auto-purged from the otp_codes table; clean it periodically if the database grows
- The `.env` file contains live secrets — never commit it (already in `.gitignore`); rotate keys if they were ever exposed

---

Built with ❤ by the Telugu Community, IIIT Allahabad.
