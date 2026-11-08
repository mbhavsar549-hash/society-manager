from datetime import datetime

from sqlalchemy import (Boolean, Column, Date, DateTime, Float, ForeignKey,
                        Integer, String, Text, UniqueConstraint)

from .database import Base

ROLES = ["admin", "secretary", "treasurer", "committee", "resident", "security", "staff", "vendor"]
COMMITTEE = ("admin", "secretary", "treasurer", "committee")


def now() -> datetime:
    return datetime.now().replace(microsecond=0)


# ---------------------------------------------------------------- people / property
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False, index=True)
    phone = Column(String)
    password_hash = Column(String, nullable=False)
    role = Column(String, default="resident")
    flat_id = Column(Integer, ForeignKey("flats.id"))
    resident_type = Column(String)  # owner / tenant
    family_members = Column(Text)
    vehicles = Column(Text)
    emergency_contact = Column(String)
    is_active = Column(Boolean, default=True)


class Building(Base):
    __tablename__ = "buildings"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    floors = Column(Integer, default=1)
    address = Column(String)


class Flat(Base):
    __tablename__ = "flats"
    id = Column(Integer, primary_key=True)
    building_id = Column(Integer, ForeignKey("buildings.id"))
    floor = Column(Integer, nullable=False)
    number = Column(String, nullable=False)
    area_sqft = Column(Float, default=0)
    bhk = Column(Integer, default=2)
    occupancy = Column(String, default="owner")  # owner / tenant / vacant
    owner_name = Column(String)
    tenant_name = Column(String)
    phone = Column(String)
    parking_slot = Column(String)


# ---------------------------------------------------------------- maintenance
class Vendor(Base):
    __tablename__ = "vendors"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    category = Column(String)
    phone = Column(String)
    email = Column(String)
    contract_start = Column(Date)
    contract_end = Column(Date)
    amount = Column(Float, default=0)
    rating = Column(Float)
    notes = Column(Text)


class MaintenanceTask(Base):
    __tablename__ = "maintenance_tasks"
    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    category = Column(String)  # water_tank, lift, generator, fire, pest, stp, cctv ...
    frequency_days = Column(Integer, default=30)
    reminder_days = Column(Integer, default=7)
    last_done = Column(Date)
    next_due = Column(Date)
    vendor_id = Column(Integer, ForeignKey("vendors.id"))
    assigned_to = Column(String)
    checklist = Column(Text)
    notes = Column(Text)
    active = Column(Boolean, default=True)
    escalated = Column(Boolean, default=False)


class MaintenanceLog(Base):
    __tablename__ = "maintenance_logs"
    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey("maintenance_tasks.id"), nullable=False)
    done_on = Column(Date)
    done_by = Column(String)
    remarks = Column(Text)
    cost = Column(Float, default=0)
    created_at = Column(DateTime, default=now)


class Asset(Base):
    __tablename__ = "assets"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    type = Column(String)
    location = Column(String)
    purchase_date = Column(Date)
    warranty_until = Column(Date)
    last_service = Column(Date)
    next_service = Column(Date)
    vendor_id = Column(Integer, ForeignKey("vendors.id"))
    notes = Column(Text)


class Inventory(Base):
    __tablename__ = "inventory"
    id = Column(Integer, primary_key=True)
    item = Column(String, nullable=False)
    quantity = Column(Float, default=0)
    min_quantity = Column(Float, default=0)
    unit = Column(String)
    location = Column(String)


# ---------------------------------------------------------------- helpdesk
class Complaint(Base):
    __tablename__ = "complaints"
    id = Column(Integer, primary_key=True)
    flat_id = Column(Integer, ForeignKey("flats.id"))
    raised_by = Column(Integer, ForeignKey("users.id"))
    title = Column(String, nullable=False)
    category = Column(String)
    priority = Column(String, default="medium")
    description = Column(Text)
    status = Column(String, default="open")  # open / in_progress / resolved / closed
    assigned_to = Column(String)
    resolution = Column(Text)
    rating = Column(Integer)
    feedback = Column(Text)
    created_at = Column(DateTime, default=now)
    resolved_at = Column(DateTime)


# ---------------------------------------------------------------- finance
class Bill(Base):
    __tablename__ = "bills"
    __table_args__ = (UniqueConstraint("flat_id", "month", name="uq_bill_flat_month"),)
    id = Column(Integer, primary_key=True)
    flat_id = Column(Integer, ForeignKey("flats.id"), nullable=False)
    month = Column(String, nullable=False)  # YYYY-MM
    base_amount = Column(Float, default=0)
    fund_amount = Column(Float, default=0)  # sinking / repair fund
    late_fee = Column(Float, default=0)
    status = Column(String, default="pending")  # pending / overdue / paid
    due_date = Column(Date)
    paid_on = Column(Date)
    payment_mode = Column(String)
    receipt_no = Column(String)


class Expense(Base):
    __tablename__ = "expenses"
    id = Column(Integer, primary_key=True)
    category = Column(String)
    description = Column(String)
    amount = Column(Float, default=0)
    date = Column(Date)
    vendor_id = Column(Integer, ForeignKey("vendors.id"))


# ---------------------------------------------------------------- community
class Notice(Base):
    __tablename__ = "notices"
    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    body = Column(Text)
    type = Column(String, default="general")  # general / emergency / event / rule
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=now)


class Poll(Base):
    __tablename__ = "polls"
    id = Column(Integer, primary_key=True)
    question = Column(String, nullable=False)
    options = Column(Text, nullable=False)  # newline separated
    closes_on = Column(Date)
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=now)


class PollVote(Base):
    __tablename__ = "poll_votes"
    __table_args__ = (UniqueConstraint("poll_id", "user_id", name="uq_vote"),)
    id = Column(Integer, primary_key=True)
    poll_id = Column(Integer, ForeignKey("polls.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    option = Column(String, nullable=False)


class Meeting(Base):
    __tablename__ = "meetings"
    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    type = Column(String, default="Committee")
    date = Column(Date)
    location = Column(String)
    agenda = Column(Text)
    attendees = Column(Text)
    minutes = Column(Text)
    action_items = Column(Text)


class Document(Base):
    __tablename__ = "documents"
    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    category = Column(String)
    url = Column(String)
    expiry_date = Column(Date)
    notes = Column(Text)


# ---------------------------------------------------------------- security
class Visitor(Base):
    __tablename__ = "visitors"
    id = Column(Integer, primary_key=True)
    flat_id = Column(Integer, ForeignKey("flats.id"))
    name = Column(String, nullable=False)
    phone = Column(String)
    kind = Column(String, default="guest")  # guest / delivery / cab / service
    purpose = Column(String)
    vehicle_no = Column(String)
    expected_on = Column(Date)
    status = Column(String, default="pending")  # pending / approved / rejected / in / out
    pass_code = Column(String)
    in_time = Column(DateTime)
    out_time = Column(DateTime)
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=now)


class Incident(Base):
    __tablename__ = "incidents"
    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    type = Column(String, default="other")
    location = Column(String)
    description = Column(Text)
    status = Column(String, default="open")
    reported_by = Column(Integer, ForeignKey("users.id"))
    reported_on = Column(DateTime, default=now)


class EmergencyContact(Base):
    __tablename__ = "emergency_contacts"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    type = Column(String)
    phone = Column(String, nullable=False)
    notes = Column(String)


# ---------------------------------------------------------------- facilities
class Amenity(Base):
    __tablename__ = "amenities"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    fee = Column(Float, default=0)
    capacity = Column(Integer)
    open_time = Column(String, default="06:00")
    close_time = Column(String, default="22:00")
    description = Column(String)


class Booking(Base):
    __tablename__ = "bookings"
    id = Column(Integer, primary_key=True)
    amenity_id = Column(Integer, ForeignKey("amenities.id"), nullable=False)
    flat_id = Column(Integer, ForeignKey("flats.id"))
    booked_by = Column(Integer, ForeignKey("users.id"))
    date = Column(Date, nullable=False)
    start_time = Column(String, nullable=False)
    end_time = Column(String, nullable=False)
    status = Column(String, default="approved")  # approved / cancelled
    fee = Column(Float, default=0)
    created_at = Column(DateTime, default=now)


class ParkingSlot(Base):
    __tablename__ = "parking"
    id = Column(Integer, primary_key=True)
    slot_no = Column(String, nullable=False)
    type = Column(String, default="resident")
    flat_id = Column(Integer, ForeignKey("flats.id"))
    vehicle_no = Column(String)
    sticker_no = Column(String)


class UtilityReading(Base):
    __tablename__ = "utility_readings"
    id = Column(Integer, primary_key=True)
    type = Column(String, default="water")
    date = Column(Date)
    value = Column(Float)
    unit = Column(String)
    notes = Column(String)


# ---------------------------------------------------------------- staff
class Staff(Base):
    __tablename__ = "staff"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    role = Column(String)
    phone = Column(String)
    shift = Column(String)
    salary = Column(Float, default=0)
    joined_on = Column(Date)
    is_active = Column(Boolean, default=True)


class StaffAttendance(Base):
    __tablename__ = "staff_attendance"
    id = Column(Integer, primary_key=True)
    staff_id = Column(Integer, ForeignKey("staff.id"), nullable=False)
    date = Column(Date)
    status = Column(String, default="present")
    check_in = Column(String)
    check_out = Column(String)


# ---------------------------------------------------------------- system
class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True)
    key = Column(String, index=True)  # de-duplication key
    message = Column(String, nullable=False)
    level = Column(String, default="info")  # info / warning / danger
    target_role = Column(String)  # None = everyone, "committee" = committee roles, or a role
    user_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=now)


class NotificationRead(Base):
    __tablename__ = "notification_reads"
    __table_args__ = (UniqueConstraint("user_id", "notification_id", name="uq_read"),)
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    notification_id = Column(Integer, ForeignKey("notifications.id"), nullable=False)


class AuditLog(Base):
    __tablename__ = "audit_log"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    user_name = Column(String)
    action = Column(String)
    entity = Column(String)
    entity_id = Column(Integer)
    detail = Column(String)
    created_at = Column(DateTime, default=now)
