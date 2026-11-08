import os
import sys
from datetime import date, timedelta

os.environ["DATABASE_URL"] = "sqlite:///./test_society.db"
os.environ["SCHEDULER"] = "0"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from fastapi.testclient import TestClient

if os.path.exists("test_society.db"):
    os.remove("test_society.db")

from app.main import app  # noqa: E402


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def login(client, email, password):
    r = client.post("/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_auth_and_rbac(client):
    assert client.post("/api/auth/login", json={"email": "admin@society.com", "password": "bad"}).status_code == 401
    assert client.get("/api/dashboard").status_code == 401
    resident = login(client, "resident@society.com", "resident123")
    # resident cannot create flats or manage users
    assert client.post("/api/flats", json={"floor": 1, "number": "999"}, headers=resident).status_code == 403
    assert client.get("/api/users", headers=resident).status_code == 403
    assert client.get("/api/expenses", headers=resident).status_code == 403


def test_overdue_maintenance_flow(client):
    sec = login(client, "secretary@society.com", "secretary123")
    dash = client.get("/api/dashboard", headers=sec).json()
    titles = [t["title"] for t in dash["overdue_tasks"]]
    assert "Water tank cleaning" in titles and any("Lift" in t for t in titles)

    tank = next(t for t in dash["overdue_tasks"] if t["title"] == "Water tank cleaning")
    r = client.post(f"/api/maintenance/tasks/{tank['id']}/complete", json={"remarks": "cleaned", "cost": 7000}, headers=sec)
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    assert r.json()["next_due"] == str(date.today() + timedelta(days=90))
    exp = client.get("/api/expenses", headers=sec).json()
    assert any(e["amount"] == 7000 for e in exp)  # cost booked automatically

    res = client.post("/api/maintenance/run-checks", headers=sec).json()
    assert res["notifications_created"] >= 1
    assert res["escalated"] >= 1  # lift is >7 days overdue
    resident = login(client, "resident@society.com", "resident123")
    items = client.get("/api/notifications", headers=resident).json()["items"]
    assert any("ESCALATION" in n["message"] for n in items)  # residents see escalations


def test_billing(client):
    tre = login(client, "treasurer@society.com", "treasurer123")
    r = client.post("/api/bills/generate", json={"month": "2031-01", "rate": 3, "fund_amount": 200}, headers=tre).json()
    assert r["created"] == 48
    assert client.post("/api/bills/generate", json={"month": "2031-01", "rate": 3}, headers=tre).json()["created"] == 0
    res = login(client, "resident@society.com", "resident123")
    bills = client.get("/api/bills", headers=res).json()
    assert bills and all(b["flat_number"] == "101" for b in bills)
    unpaid = next(b for b in bills if b["status"] != "paid")
    paid = client.post(f"/api/bills/{unpaid['id']}/pay", json={"payment_mode": "UPI"}, headers=res).json()
    assert paid["status"] == "paid" and paid["receipt_no"]
    assert client.post(f"/api/bills/{unpaid['id']}/pay", headers=res).status_code == 400
    assert client.get("/api/bills/finance-report", headers=tre).json()["total_income"] > 0
    assert client.get("/api/bills/defaulters", headers=tre).status_code == 200
    assert client.post("/api/bills/apply-late-fees", json={"percent": 2}, headers=tre).status_code == 200


def test_visitors_and_complaints(client):
    res = login(client, "resident@society.com", "resident123")
    guard = login(client, "guard@society.com", "guard123")
    v = client.post("/api/visitors", json={"name": "Friend", "kind": "guest"}, headers=res).json()
    assert v["status"] == "approved" and len(v["pass_code"]) == 6
    assert client.post("/api/visitors/verify", json={"pass_code": v["pass_code"]}, headers=guard).status_code == 200
    assert client.post(f"/api/visitors/{v['id']}/checkin", headers=guard).json()["status"] == "in"
    assert client.post(f"/api/visitors/{v['id']}/checkout", headers=guard).json()["status"] == "out"

    g = client.post("/api/visitors", json={"name": "Courier", "flat_id": 1}, headers=guard).json()
    assert g["status"] == "pending"
    assert client.post(f"/api/visitors/{g['id']}/checkin", headers=guard).status_code == 400  # needs approval

    c = client.post("/api/complaints", json={"title": "Leak", "category": "plumbing", "priority": "high"}, headers=res).json()
    sec = login(client, "secretary@society.com", "secretary123")
    assert client.put(f"/api/complaints/{c['id']}", json={"status": "resolved", "resolution": "fixed"}, headers=sec).json()["resolved_at"]
    assert client.post(f"/api/complaints/{c['id']}/rate", json={"rating": 5}, headers=res).json()["rating"] == 5


def test_bookings_polls_sos(client):
    res = login(client, "resident@society.com", "resident123")
    day = str(date.today() + timedelta(days=3))
    body = {"amenity_id": 1, "date": day, "start_time": "10:00", "end_time": "12:00"}
    assert client.post("/api/bookings", json=body, headers=res).status_code == 200
    assert client.post("/api/bookings", json={**body, "start_time": "11:00", "end_time": "13:00"}, headers=res).status_code == 409
    assert client.post("/api/bookings", json={**body, "start_time": "01:00", "end_time": "02:00"}, headers=res).status_code == 422

    poll = client.get("/api/polls", headers=res).json()[0]
    voted = client.post(f"/api/polls/{poll['id']}/vote", json={"option": "Sunday"}, headers=res).json()
    assert voted["my_vote"] == "Sunday" and voted["counts"]["Sunday"] == 1

    assert client.post("/api/sos", json={"message": "help"}, headers=res).json()["ok"]
    sec = login(client, "secretary@society.com", "secretary123")
    assert len(client.get("/api/audit", headers=sec).json()) > 0
    assert client.get("/api/reports/compliance", headers=res).status_code == 200


def test_staff_salary_hidden_from_guard(client):
    guard = login(client, "guard@society.com", "guard123")
    rows = client.get("/api/staff", headers=guard).json()
    assert rows and all("salary" not in r for r in rows)
    sec = login(client, "secretary@society.com", "secretary123")
    assert all("salary" in r for r in client.get("/api/staff", headers=sec).json())
