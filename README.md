# Society Manager — complete building / apartment society management system

**Backend:** Python · FastAPI · SQLAlchemy · SQLite (PostgreSQL-ready) · JWT auth · APScheduler
**Frontend:** React 18 · Vite · React Router

Example it solves: *a 12-floor building where the water tank was not cleaned on time and lift
maintenance was skipped.* Every recurring duty has a due date, reminders, overdue alerts,
auto-escalation, a public (resident-visible) compliance view and an audit trail.

## Run it (two terminals)

### 1. Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
API docs (Swagger): http://localhost:8000/docs — a demo database (48 flats, 12 floors) is created on first run.

### 2. Frontend
```bash
cd frontend
npm install
npm run dev
```
Open http://localhost:5173 (the dev server proxies `/api` to port 8000).

### Demo logins
| Role | Email | Password |
|---|---|---|
| Admin | admin@society.com | admin123 |
| Secretary | secretary@society.com | secretary123 |
| Treasurer | treasurer@society.com | treasurer123 |
| Security guard | guard@society.com | guard123 |
| Maintenance staff | staff@society.com | staff123 |
| Resident (flat 101) | resident@society.com | resident123 |

Reset the data: stop the server, delete `backend/society.db`, start again.
Run tests: `cd backend && python -m pytest`.

## Deploy online
See **DEPLOYMENT.md** (frontend on Netlify, API + PostgreSQL on Render).

## Modules

| # | Module | What it does | Where |
|---|---|---|---|
| 1 | Users & roles | Login, self-registration, 8 roles, role-based access, profile, password change | `routers/auth.py`, `routers/users.py` |
| 2 | Building / floors / flats | Buildings, flats, owner/tenant, parking slot | generic CRUD (`crud.py`) |
| 3 | **Maintenance scheduler** | Water tank, lift AMC, generator, fire, pest, STP… repeat every N days, "mark done" reschedules automatically, history, cost auto-booked as expense | `routers/maintenance.py` |
| 4 | Complaints / helpdesk | Raise, assign, status flow, SLA breach flag, rating after resolution | `routers/complaints.py` |
| 5 | Billing & finance | Generate monthly bills (per sq ft / fixed + sinking fund), pay + receipt, late fees, defaulters, income/expense report, expenses | `routers/billing.py` |
| 6 | Visitors & security | Resident pre-approval with 6-digit gate pass, guard-logged visitors need resident approval, check-in/out, incidents | `routers/visitors.py` |
| 7 | Notices & communication | Notice board, in-app notifications, broadcast alerts, polls & voting | `routers/community.py` |
| 8 | Meetings | Agenda, minutes, attendees, action items | generic CRUD |
| 9 | Amenity booking | Slot booking with opening hours, clash detection, fees, cancel | `routers/bookings.py` |
| 10 | Parking | Slot allocation, vehicle, sticker | generic CRUD |
| 11 | Utilities | Water, electricity, generator fuel, garbage readings | generic CRUD |
| 12 | Vendors & AMC | Directory, contract end dates (auto reminder), rating | generic CRUD |
| 13 | Assets & inventory | Asset register with warranty/service dates, stock with minimum level | generic CRUD |
| 14 | Staff | Records, shifts, salary (hidden from guards), attendance | generic CRUD |
| 15 | Documents | Registers, licences with expiry reminders | generic CRUD |
| 16 | Dashboard & reports | Overdue / due soon, dues, complaints, compliance report | `routers/dashboard.py` |
| 17 | **Reminder engine** | Daily 08:00 job: due-soon + overdue alerts, **escalation to all residents after 7 days**, asset/vendor/document expiry, marks overdue bills | `jobs.py` |
| 18 | Emergency & safety | SOS button (alerts everyone + logs incident), emergency directory | `routers/community.py` |
| 19 | Accountability | Audit log of every change; overdue tasks visible to all residents | `deps.audit`, `/audit` |

Adding another master-data screen takes ~10 lines: add a model in `models.py`, one line in `RESOURCES`
(`main.py`) and one config block in `frontend/src/resources.js`.

## Roles (summary)
- **Secretary / Admin** — everything. **Treasurer** — billing and expenses. **Committee** — oversight, maintenance, notices.
- **Resident** — own bills, complaints, visitors, bookings; sees all overdue maintenance. **Security** — visitors, gate pass, incidents, attendance.
- **Staff** — mark maintenance done, inventory, readings.

## Not included (needs external accounts or hardware — hook points are marked in code)
- **Real payment gateway** (Razorpay/Stripe): `POST /api/bills/{id}/pay` currently records the payment; verify the gateway payment there.
- **SMS / WhatsApp / email / push delivery**: notifications are stored and shown in-app; send externally from `jobs._notify` and `/api/notifications/broadcast`.
- **File/photo upload** (completion photos, documents): documents store a link for now.
- IoT sensors, AI prediction, intercom, multi-society (multi-tenant) support, OTP password reset, mobile apps.

## Before production
Set a strong `SECRET_KEY`, use PostgreSQL, serve behind HTTPS, restrict `CORS_ORIGINS`, change the demo passwords
(or start with `SEED=0` and create your own admin), and add Alembic migrations when you change models.
