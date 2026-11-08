"""Recurring maintenance: water tank cleaning, lift AMC, generator, fire safety, etc."""
from datetime import date, timedelta

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from ..crud import coerce, to_dict
from ..database import get_db
from ..deps import audit, guard
from ..models import Expense, MaintenanceLog, MaintenanceTask, User, Vendor

router = APIRouter(prefix="/api/maintenance", tags=["maintenance"])
MANAGE = ("secretary", "committee", "treasurer")
EXECUTE = ("secretary", "committee", "staff", "vendor")


def task_status(task: MaintenanceTask, today: date | None = None) -> tuple[str, int | None]:
    today = today or date.today()
    if not task.next_due:
        return "unscheduled", None
    days_left = (task.next_due - today).days
    if days_left < 0:
        return "overdue", days_left
    if days_left <= (task.reminder_days or 0):
        return "due_soon", days_left
    return "ok", days_left


def serialize_task(task: MaintenanceTask, vendors: dict | None = None) -> dict:
    d = to_dict(task)
    d["status"], d["days_left"] = task_status(task)
    d["vendor_name"] = (vendors or {}).get(task.vendor_id)
    return d


def vendor_map(db: Session) -> dict:
    return {v.id: v.name for v in db.query(Vendor).all()}


@router.get("/tasks")
def list_tasks(db: Session = Depends(get_db), user: User = guard()):
    """Visible to every resident on purpose: transparency about what is overdue."""
    vendors = vendor_map(db)
    tasks = [serialize_task(t, vendors) for t in db.query(MaintenanceTask).order_by(MaintenanceTask.next_due)]
    order = {"overdue": 0, "due_soon": 1, "ok": 2, "unscheduled": 3}
    return sorted(tasks, key=lambda t: (order[t["status"]], t["next_due"] or date.max))


@router.post("/tasks")
def create_task(data: dict = Body(...), db: Session = Depends(get_db), user: User = guard(*MANAGE)):
    fields = coerce(MaintenanceTask, data, skip=("id", "escalated"))
    if not fields.get("title"):
        raise HTTPException(422, "Title is required")
    freq = fields.get("frequency_days") or 30
    fields["frequency_days"] = freq
    if not fields.get("next_due"):
        last = fields.get("last_done")
        fields["next_due"] = last + timedelta(days=freq) if last else date.today()
    task = MaintenanceTask(**fields)
    db.add(task)
    db.flush()
    audit(db, user, "create", "maintenance_task", task.id, task.title)
    db.commit()
    return serialize_task(task, vendor_map(db))


@router.put("/tasks/{task_id}")
def update_task(task_id: int, data: dict = Body(...), db: Session = Depends(get_db), user: User = guard(*MANAGE)):
    task = db.get(MaintenanceTask, task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    for k, v in coerce(MaintenanceTask, data, skip=("id", "escalated")).items():
        setattr(task, k, v)
    audit(db, user, "update", "maintenance_task", task.id, task.title)
    db.commit()
    return serialize_task(task, vendor_map(db))


@router.delete("/tasks/{task_id}")
def delete_task(task_id: int, db: Session = Depends(get_db), user: User = guard(*MANAGE)):
    task = db.get(MaintenanceTask, task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    db.query(MaintenanceLog).filter(MaintenanceLog.task_id == task_id).delete()
    db.delete(task)
    audit(db, user, "delete", "maintenance_task", task_id, task.title)
    db.commit()
    return {"ok": True}


@router.post("/tasks/{task_id}/complete")
def complete_task(task_id: int, data: dict = Body(default={}), db: Session = Depends(get_db),
                  user: User = guard(*EXECUTE)):
    """Record that the work was done: writes a log, reschedules next_due, books the cost as an expense."""
    task = db.get(MaintenanceTask, task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    f = coerce(MaintenanceLog, data, skip=("id", "task_id"))
    done_on = f.get("done_on") or date.today()
    cost = f.get("cost") or 0
    log = MaintenanceLog(task_id=task.id, done_on=done_on, done_by=f.get("done_by") or user.name,
                         remarks=f.get("remarks"), cost=cost)
    db.add(log)
    task.last_done = done_on
    task.next_due = done_on + timedelta(days=task.frequency_days or 30)
    task.escalated = False
    if cost > 0:
        db.add(Expense(category="maintenance", description=f"{task.title} (auto from maintenance log)",
                       amount=cost, date=done_on, vendor_id=task.vendor_id))
    audit(db, user, "complete", "maintenance_task", task.id, task.title)
    db.commit()
    return serialize_task(task, vendor_map(db))


@router.get("/logs")
def list_logs(task_id: int | None = None, db: Session = Depends(get_db), user: User = guard()):
    q = db.query(MaintenanceLog)
    if task_id:
        q = q.filter(MaintenanceLog.task_id == task_id)
    titles = {t.id: t.title for t in db.query(MaintenanceTask).all()}
    out = []
    for log in q.order_by(MaintenanceLog.id.desc()).limit(200):
        d = to_dict(log)
        d["task_title"] = titles.get(log.task_id)
        out.append(d)
    return out


@router.post("/run-checks")
def run_checks_now(db: Session = Depends(get_db), user: User = guard("secretary")):
    from ..jobs import run_checks
    return run_checks(db)
