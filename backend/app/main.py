import os
from contextlib import asynccontextmanager
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import models
from .crud import make_router
from .database import Base, SessionLocal, engine
from .jobs import run_checks, scheduled_job
from .routers import auth, billing, bookings, community, complaints, dashboard, maintenance, users, visitors
from .seed import bootstrap_admin, seed

COMMITTEE = ("secretary", "treasurer", "committee")
M = models


def set_creator(obj, user):
    if hasattr(obj, "created_by"):
        obj.created_by = user.id
    if hasattr(obj, "reported_by"):
        obj.reported_by = user.id


# (url prefix, model, read roles, write roles[, redaction])   -- None = any logged-in user. Admin is always allowed.
RESOURCES = [
    ("buildings", M.Building, None, ("secretary",)),
    ("flats", M.Flat, None, ("secretary",)),
    ("vendors", M.Vendor, None, ("secretary", "committee")),
    ("assets", M.Asset, None, ("secretary", "committee")),
    ("inventory", M.Inventory, COMMITTEE + ("staff",), ("secretary", "committee", "staff")),
    ("expenses", M.Expense, COMMITTEE, ("secretary", "treasurer")),
    ("notices", M.Notice, None, ("secretary", "committee")),
    ("amenities", M.Amenity, None, ("secretary",)),
    ("meetings", M.Meeting, None, ("secretary", "committee")),
    ("documents", M.Document, None, ("secretary", "committee")),
    ("staff", M.Staff, COMMITTEE + ("security",), ("secretary",), (["salary"], COMMITTEE)),
    ("staff-attendance", M.StaffAttendance, COMMITTEE + ("security",), ("secretary", "security")),
    ("parking", M.ParkingSlot, COMMITTEE + ("security",), ("secretary", "security")),
    ("utility-readings", M.UtilityReading, COMMITTEE + ("staff", "security"), ("secretary", "staff", "security")),
    ("emergency-contacts", M.EmergencyContact, None, ("secretary",)),
    ("incidents", M.Incident, COMMITTEE + ("security",), ("secretary", "committee", "security")),
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    if os.getenv("SEED", "1") == "1":
        seed()
    else:
        bootstrap_admin()  # creates the first admin from ADMIN_EMAIL / ADMIN_PASSWORD if the database is empty
    scheduler = None
    if os.getenv("SCHEDULER", "1") == "1":
        db = SessionLocal()
        try:
            run_checks(db)  # catch up on startup
        finally:
            db.close()
        try:
            # Explicit timezone: avoids tzlocal errors on machines with legacy TZ names (e.g. "Asia/Calcutta").
            tz = ZoneInfo(os.getenv("SCHEDULER_TZ", "Asia/Kolkata"))
            scheduler = BackgroundScheduler(timezone=tz)
            scheduler.add_job(scheduled_job, "cron", hour=8, minute=0)  # every day at 08:00
            scheduler.start()
        except Exception as exc:  # never let the scheduler stop the API from starting
            print(f"[warn] daily reminder scheduler not started: {exc}")
            scheduler = None
    yield
    if scheduler:
        scheduler.shutdown(wait=False)


app = FastAPI(title="Society Management API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip().rstrip("/") for o in
                   os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",") if o.strip()],
    # optional: allow all Netlify deploy previews, e.g. CORS_ORIGIN_REGEX=https://.*--my-site\\.netlify\\.app
    allow_origin_regex=os.getenv("CORS_ORIGIN_REGEX") or None,
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

for router in (auth.router, users.router, maintenance.router, billing.router, complaints.router,
               visitors.router, bookings.router, community.router, dashboard.router):
    app.include_router(router)

for prefix, model, read, write, *extra in RESOURCES:
    app.include_router(make_router(prefix, model, read=read, write=write, hook=set_creator,
                                   redact=extra[0] if extra else None))


@app.get("/api/health")
def health():
    return {"status": "ok"}
