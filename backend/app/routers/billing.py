"""Maintenance bills, payments, late fees, defaulters and finance reports."""
import calendar
from collections import defaultdict
from datetime import date

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from ..crud import coerce, to_dict
from ..database import get_db
from ..deps import audit, guard
from ..models import Bill, Expense, Flat, User

router = APIRouter(prefix="/api/bills", tags=["billing"])
FINANCE = ("secretary", "treasurer")
VIEW_ALL = ("secretary", "treasurer", "committee")


def ser(bill: Bill, flats: dict) -> dict:
    d = to_dict(bill)
    d["total"] = round((bill.base_amount or 0) + (bill.fund_amount or 0) + (bill.late_fee or 0), 2)
    d["flat_number"] = flats.get(bill.flat_id)
    return d


def flat_map(db: Session) -> dict:
    return {f.id: f.number for f in db.query(Flat).all()}


@router.get("")
def list_bills(status: str | None = None, month: str | None = None, flat_id: int | None = None,
               db: Session = Depends(get_db), user: User = guard("resident", *VIEW_ALL)):
    q = db.query(Bill)
    if user.role == "resident":
        q = q.filter(Bill.flat_id == (user.flat_id or -1))
    elif flat_id:
        q = q.filter(Bill.flat_id == flat_id)
    if status:
        q = q.filter(Bill.status == status)
    if month:
        q = q.filter(Bill.month == month)
    flats = flat_map(db)
    return [ser(b, flats) for b in q.order_by(Bill.month.desc(), Bill.flat_id)]


@router.post("/generate")
def generate(data: dict = Body(...), db: Session = Depends(get_db), user: User = guard(*FINANCE)):
    """Create one bill per flat for a month. mode = per_sqft | fixed."""
    month = data.get("month")
    try:
        year, mon = [int(x) for x in month.split("-")]
        date(year, mon, 1)
    except Exception:
        raise HTTPException(422, "month must be in YYYY-MM format")
    mode = data.get("mode", "per_sqft")
    rate = float(data.get("rate") or 0)
    fund = float(data.get("fund_amount") or 0)
    if rate <= 0:
        raise HTTPException(422, "rate must be greater than 0")
    due = data.get("due_date")
    due_date = date.fromisoformat(due) if due else date(year, mon, min(10, calendar.monthrange(year, mon)[1]))

    created = skipped = 0
    for flat in db.query(Flat).filter(Flat.occupancy != "vacant").all():
        if db.query(Bill).filter(Bill.flat_id == flat.id, Bill.month == month).first():
            skipped += 1
            continue
        base = rate * (flat.area_sqft or 0) if mode == "per_sqft" else rate
        db.add(Bill(flat_id=flat.id, month=month, base_amount=round(base, 2), fund_amount=fund, due_date=due_date))
        created += 1
    audit(db, user, "generate", "bills", None, f"{month}: {created} created, {skipped} skipped")
    db.commit()
    return {"created": created, "skipped": skipped}


@router.post("/apply-late-fees")
def apply_late_fees(data: dict = Body(default={}), db: Session = Depends(get_db), user: User = guard(*FINANCE)):
    """Add a late fee (percent of base amount, or flat amount) to every unpaid bill past its due date."""
    percent = float(data.get("percent") or 0)
    flat_fee = float(data.get("flat_fee") or 0)
    if percent <= 0 and flat_fee <= 0:
        raise HTTPException(422, "Provide percent or flat_fee")
    count = 0
    for b in db.query(Bill).filter(Bill.status != "paid", Bill.due_date < date.today(), Bill.late_fee == 0).all():
        b.late_fee = round((b.base_amount or 0) * percent / 100, 2) if percent else flat_fee
        b.status = "overdue"
        count += 1
    audit(db, user, "late_fees", "bills", None, f"{count} bills")
    db.commit()
    return {"updated": count}


@router.post("/{bill_id}/pay")
def pay(bill_id: int, data: dict = Body(default={}), db: Session = Depends(get_db),
        user: User = guard("resident", *FINANCE)):
    """Mark paid. Plug a real gateway (Razorpay/Stripe) in here: verify the payment, then set status."""
    bill = db.get(Bill, bill_id)
    if not bill:
        raise HTTPException(404, "Bill not found")
    if user.role == "resident" and bill.flat_id != user.flat_id:
        raise HTTPException(403, "This bill belongs to another flat")
    if bill.status == "paid":
        raise HTTPException(400, "Bill already paid")
    bill.status = "paid"
    bill.paid_on = date.today()
    bill.payment_mode = data.get("payment_mode") or "UPI"
    bill.receipt_no = f"RCPT-{bill.month.replace('-', '')}-{bill.id:05d}"
    audit(db, user, "pay", "bills", bill.id, bill.receipt_no)
    db.commit()
    return ser(bill, flat_map(db))


@router.get("/defaulters")
def defaulters(db: Session = Depends(get_db), user: User = guard(*VIEW_ALL)):
    flats = {f.id: f for f in db.query(Flat).all()}
    totals = defaultdict(lambda: {"months": 0, "amount": 0.0})
    for b in db.query(Bill).filter(Bill.status != "paid", Bill.due_date < date.today()):
        totals[b.flat_id]["months"] += 1
        totals[b.flat_id]["amount"] += (b.base_amount or 0) + (b.fund_amount or 0) + (b.late_fee or 0)
    rows = [{"flat_id": fid, "flat_number": flats[fid].number if fid in flats else fid,
             "owner_name": flats[fid].owner_name if fid in flats else None,
             "months_due": v["months"], "amount_due": round(v["amount"], 2)} for fid, v in totals.items()]
    return sorted(rows, key=lambda r: -r["amount_due"])


@router.get("/finance-report")
def finance_report(db: Session = Depends(get_db), user: User = guard(*VIEW_ALL)):
    income = defaultdict(float)
    for b in db.query(Bill).filter(Bill.status == "paid"):
        key = (b.paid_on or date.today()).strftime("%Y-%m")
        income[key] += (b.base_amount or 0) + (b.fund_amount or 0) + (b.late_fee or 0)
    expense = defaultdict(float)
    by_category = defaultdict(float)
    for e in db.query(Expense):
        key = (e.date or date.today()).strftime("%Y-%m")
        expense[key] += e.amount or 0
        by_category[e.category or "other"] += e.amount or 0
    months = sorted(set(income) | set(expense))
    pending = sum((b.base_amount or 0) + (b.fund_amount or 0) + (b.late_fee or 0)
                  for b in db.query(Bill).filter(Bill.status != "paid"))
    return {
        "months": [{"month": m, "income": round(income[m], 2), "expense": round(expense[m], 2),
                    "net": round(income[m] - expense[m], 2)} for m in months],
        "expense_by_category": [{"category": k, "amount": round(v, 2)} for k, v in sorted(by_category.items())],
        "total_income": round(sum(income.values()), 2),
        "total_expense": round(sum(expense.values()), 2),
        "pending_dues": round(pending, 2),
    }
