from datetime import date

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from ..crud import coerce, to_dict
from ..database import get_db
from ..deps import audit, guard
from ..models import COMMITTEE, Amenity, Booking, Flat, User

router = APIRouter(prefix="/api/bookings", tags=["bookings"])


def ser(b: Booking, amenities: dict, flats: dict) -> dict:
    d = to_dict(b)
    d["amenity_name"] = amenities.get(b.amenity_id)
    d["flat_number"] = flats.get(b.flat_id)
    return d


def maps(db):
    return ({a.id: a.name for a in db.query(Amenity)}, {f.id: f.number for f in db.query(Flat)})


@router.get("")
def list_bookings(upcoming: bool = False, db: Session = Depends(get_db), user: User = guard()):
    q = db.query(Booking)
    if upcoming:
        q = q.filter(Booking.date >= date.today(), Booking.status == "approved")
    am, fl = maps(db)
    return [ser(b, am, fl) for b in q.order_by(Booking.date.desc(), Booking.start_time)]


@router.post("")
def create_booking(data: dict = Body(...), db: Session = Depends(get_db), user: User = guard("resident", *COMMITTEE)):
    f = coerce(Booking, data, skip=("id", "status", "fee", "booked_by", "created_at"))
    for required in ("amenity_id", "date", "start_time", "end_time"):
        if not f.get(required):
            raise HTTPException(422, f"{required} is required")
    if f["start_time"] >= f["end_time"]:
        raise HTTPException(422, "End time must be after start time")
    if f["date"] < date.today():
        raise HTTPException(422, "Cannot book a past date")
    amenity = db.get(Amenity, f["amenity_id"])
    if not amenity:
        raise HTTPException(404, "Amenity not found")
    if f["start_time"] < (amenity.open_time or "00:00") or f["end_time"] > (amenity.close_time or "23:59"):
        raise HTTPException(422, f"{amenity.name} is open {amenity.open_time} - {amenity.close_time}")
    clash = db.query(Booking).filter(
        Booking.amenity_id == amenity.id, Booking.date == f["date"], Booking.status == "approved",
        Booking.start_time < f["end_time"], Booking.end_time > f["start_time"]).first()
    if clash:
        raise HTTPException(409, f"Slot clashes with an existing booking ({clash.start_time}-{clash.end_time})")
    if user.role == "resident":
        f["flat_id"] = user.flat_id
    b = Booking(**f, booked_by=user.id, fee=amenity.fee or 0, status="approved")
    db.add(b)
    db.flush()
    audit(db, user, "create", "booking", b.id, amenity.name)
    db.commit()
    return ser(b, *maps(db))


@router.post("/{booking_id}/cancel")
def cancel(booking_id: int, db: Session = Depends(get_db), user: User = guard()):
    b = db.get(Booking, booking_id)
    if not b:
        raise HTTPException(404, "Booking not found")
    if b.booked_by != user.id and user.role not in COMMITTEE:
        raise HTTPException(403, "You can only cancel your own bookings")
    b.status = "cancelled"
    audit(db, user, "cancel", "booking", b.id)
    db.commit()
    return ser(b, *maps(db))
