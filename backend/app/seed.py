"""Demo data so the app is useful on first run. Delete society.db to reseed."""
from datetime import date, timedelta

from .database import SessionLocal
from .models import (Amenity, Asset, Bill, Building, Complaint, Document, EmergencyContact, Expense, Flat,
                     Inventory, MaintenanceLog, MaintenanceTask, Meeting, Notice, Poll, Staff, UtilityReading,
                     User, Vendor, Visitor, now)
from .security import hash_password

FLOORS, FLATS_PER_FLOOR = 12, 4

DEMO_USERS = [
    ("Admin", "admin@society.com", "admin123", "admin", None),
    ("Sandeep Secretary", "secretary@society.com", "secretary123", "secretary", None),
    ("Tina Treasurer", "treasurer@society.com", "treasurer123", "treasurer", None),
    ("Mohan Guard", "guard@society.com", "guard123", "security", None),
    ("Ravi Technician", "staff@society.com", "staff123", "staff", None),
    ("Rita Resident", "resident@society.com", "resident123", "resident", "101"),
    ("Raj Resident", "resident2@society.com", "resident123", "resident", "502"),
]


def seed():
    db = SessionLocal()
    try:
        if db.query(User).count():
            return
        today = date.today()

        b = Building(name="Sunrise Heights", floors=FLOORS, address="12 Lake Road, Pune")
        db.add(b)
        db.flush()
        flats = {}
        for floor in range(1, FLOORS + 1):
            for n in range(1, FLATS_PER_FLOOR + 1):
                number = f"{floor}{n:02d}"
                f = Flat(building_id=b.id, floor=floor, number=number, area_sqft=950 + 100 * (n % 3), bhk=2 + (n % 2),
                         occupancy="tenant" if (floor + n) % 7 == 0 else "owner", owner_name=f"Owner of {number}",
                         parking_slot=f"P-{number}")
                db.add(f)
                flats[number] = f
        db.flush()

        for name, email, pw, role, flat_no in DEMO_USERS:
            db.add(User(name=name, email=email, password_hash=hash_password(pw), role=role,
                        flat_id=flats[flat_no].id if flat_no else None, phone="9000000000",
                        resident_type="owner" if role == "resident" else None))

        vendors = {
            "lift": Vendor(name="Otis Lift Services", category="Lift AMC", phone="9811111111",
                           contract_start=today - timedelta(days=300), contract_end=today + timedelta(days=20), amount=120000, rating=4),
            "tank": Vendor(name="AquaClean Tank Cleaners", category="Water tank", phone="9822222222",
                           contract_end=today + timedelta(days=200), amount=30000, rating=3.5),
            "gen": Vendor(name="PowerGen Services", category="Generator", phone="9833333333",
                          contract_end=today + timedelta(days=150), amount=40000, rating=4.5),
            "fire": Vendor(name="SafeFire Co", category="Fire safety", phone="9844444444",
                           contract_end=today + timedelta(days=90), amount=25000),
        }
        db.add_all(vendors.values())
        db.flush()

        def task(title, cat, freq, last_done_days_ago, vendor=None, checklist=None):
            last = today - timedelta(days=last_done_days_ago)
            t = MaintenanceTask(title=title, category=cat, frequency_days=freq, last_done=last,
                                next_due=last + timedelta(days=freq), vendor_id=vendors[vendor].id if vendor else None,
                                checklist=checklist, assigned_to="Secretary")
            db.add(t)
            return t

        # Deliberately overdue so the dashboard shows the problem from the user's example
        tank = task("Water tank cleaning", "water_tank", 90, 110, "tank", "Drain tank\nScrub walls\nDisinfect\nRefill + water test")
        lift = task("Lift maintenance (AMC service)", "lift", 30, 47, "lift", "Check ropes\nBrakes\nDoor sensors\nEmergency alarm")
        task("Generator service", "generator", 30, 26, "gen", "Oil + filter\nBattery\nFuel level")
        task("Fire extinguisher inspection", "fire", 180, 170, "fire")
        task("Pest control", "pest", 60, 15)
        task("STP maintenance", "stp", 30, 5)
        task("Terrace & drainage cleaning", "cleaning", 90, 40)
        db.flush()
        db.add(MaintenanceLog(task_id=tank.id, done_on=tank.last_done, done_by="AquaClean team", remarks="Done with water test", cost=6500))
        db.add(MaintenanceLog(task_id=lift.id, done_on=lift.last_done, done_by="Otis technician", remarks="Door sensor replaced", cost=0))

        db.add_all([
            Amenity(name="Clubhouse", fee=500, capacity=40, open_time="08:00", close_time="22:00", description="Hall with kitchenette"),
            Amenity(name="Gym", fee=0, capacity=12, open_time="05:00", close_time="22:00"),
            Amenity(name="Party Hall", fee=2000, capacity=80, open_time="09:00", close_time="23:00"),
            Amenity(name="Badminton Court", fee=100, capacity=4, open_time="06:00", close_time="21:00"),
        ])
        db.add_all([
            Notice(title="Water tank cleaning scheduled", body="Water supply will be affected for 4 hours during cleaning.", type="general"),
            Notice(title="Annual General Meeting", body="AGM on the first Sunday of next month, 11 AM at the Clubhouse.", type="event"),
        ])
        db.add_all([
            EmergencyContact(name="Fire Brigade", type="Fire", phone="101"),
            EmergencyContact(name="Police", type="Police", phone="100"),
            EmergencyContact(name="Ambulance", type="Medical", phone="108"),
            EmergencyContact(name="Lift Emergency (Otis)", type="Lift", phone="9811111111"),
        ])
        db.add_all([
            Asset(name="Lift A", type="Lift", location="Main lobby", warranty_until=today + timedelta(days=400),
                  last_service=today - timedelta(days=47), next_service=today - timedelta(days=17), vendor_id=vendors["lift"].id),
            Asset(name="DG Set 125 kVA", type="Generator", location="Basement", next_service=today + timedelta(days=4), vendor_id=vendors["gen"].id),
            Asset(name="Overhead Tank 20,000 L", type="Water tank", location="Terrace"),
        ])
        db.add_all([Inventory(item="Diesel", quantity=80, min_quantity=100, unit="litre", location="Generator room"),
                    Inventory(item="Light bulbs (LED)", quantity=40, min_quantity=10, unit="pcs", location="Store")])
        db.add_all([
            Staff(name="Mohan Singh", role="Security", phone="9000000011", shift="Day", salary=15000, joined_on=today - timedelta(days=500)),
            Staff(name="Kamal Yadav", role="Security", phone="9000000012", shift="Night", salary=16000, joined_on=today - timedelta(days=300)),
            Staff(name="Sunita Devi", role="Housekeeping", phone="9000000013", shift="Day", salary=12000, joined_on=today - timedelta(days=200)),
        ])
        db.add_all([
            Document(title="Society Registration Certificate", category="Legal"),
            Document(title="Lift Licence (Lift A)", category="Licence", expiry_date=today + timedelta(days=25)),
            Document(title="Fire NOC", category="Licence", expiry_date=today + timedelta(days=300)),
        ])
        db.add(Meeting(title="Monthly committee meeting", type="Committee", date=today + timedelta(days=7), location="Clubhouse",
                       agenda="1. Overdue maintenance review\n2. Lift AMC renewal\n3. Budget"))
        db.add(Poll(question="Which day should we schedule water tank cleaning?", options="Saturday\nSunday\nWeekday", closes_on=today + timedelta(days=10)))
        db.add_all([UtilityReading(type="water", date=today - timedelta(days=i), value=18000 + i * 120, unit="litre") for i in range(0, 5)])
        db.add_all([
            Expense(category="salary", description="Staff salaries", amount=43000, date=today - timedelta(days=5)),
            Expense(category="electricity", description="Common area electricity", amount=28000, date=today - timedelta(days=9)),
            Expense(category="maintenance", description="Tank cleaning", amount=6500, date=today - timedelta(days=110), vendor_id=vendors["tank"].id),
        ])

        month = today.strftime("%Y-%m")
        last_month = (today.replace(day=1) - timedelta(days=1))
        for number, f in flats.items():
            db.add(Bill(flat_id=f.id, month=last_month.strftime("%Y-%m"), base_amount=round(3.0 * f.area_sqft, 2), fund_amount=300,
                        due_date=last_month.replace(day=10), status="paid" if int(number) % 3 else "overdue",
                        paid_on=last_month.replace(day=8) if int(number) % 3 else None,
                        receipt_no=f"RCPT-{last_month:%Y%m}-{f.id:05d}" if int(number) % 3 else None, payment_mode="UPI" if int(number) % 3 else None))
            db.add(Bill(flat_id=f.id, month=month, base_amount=round(3.0 * f.area_sqft, 2), fund_amount=300,
                        due_date=today.replace(day=10) if today.day <= 10 else today + timedelta(days=5)))

        db.flush()
        resident = db.query(User).filter(User.email == "resident@society.com").first()
        db.add(Complaint(flat_id=resident.flat_id, raised_by=resident.id, title="Lift B jerks between floors 5 and 6", category="lift",
                         priority="high", description="Happens every morning.", created_at=now() - timedelta(days=3)))
        db.add(Complaint(flat_id=resident.flat_id, raised_by=resident.id, title="Corridor light not working", category="electrical", priority="low"))
        db.add(Visitor(flat_id=resident.flat_id, name="Amazon delivery", kind="delivery", status="pending", created_by=resident.id))
        db.commit()
    finally:
        db.close()


def bootstrap_admin():
    """Production start (SEED=0): create the first admin from env vars when there are no users yet."""
    import os
    email, password = os.getenv("ADMIN_EMAIL"), os.getenv("ADMIN_PASSWORD")
    if not email or not password:
        return
    db = SessionLocal()
    try:
        if db.query(User).count() == 0:
            db.add(User(name=os.getenv("ADMIN_NAME", "Administrator"), email=email.lower().strip(),
                        password_hash=hash_password(password), role="admin"))
            db.commit()
            print(f"[info] first admin created: {email}")
    finally:
        db.close()
