// Config-driven master-data pages. Each entry becomes a full list/add/edit/delete screen (CrudPage).
// field.type: text | number | date | time | select | textarea | checkbox | ref | password
// field.list: show as a table column.  field.ref: endpoint to load options from.

const C = ["secretary", "treasurer", "committee"]; // admin is always allowed

export const REF_LABEL = {
  "/flats": (f) => `${f.number} (Floor ${f.floor})`,
  "/buildings": (b) => b.name,
  "/vendors": (v) => `${v.name}${v.category ? " – " + v.category : ""}`,
  "/staff": (s) => s.name,
  "/amenities": (a) => a.name,
};
export const refLabel = (endpoint, item) => (REF_LABEL[endpoint] ? REF_LABEL[endpoint](item) : item.name || item.title || item.id);

const flat = { name: "flat_id", label: "Flat", type: "ref", ref: "/flats", list: true };
const vendor = { name: "vendor_id", label: "Vendor", type: "ref", ref: "/vendors" };

export const RESOURCES = [
  {
    key: "flats", label: "Flats", icon: "🏢", group: "Property", endpoint: "/flats", write: ["secretary"],
    fields: [
      { name: "building_id", label: "Building", type: "ref", ref: "/buildings" },
      { name: "floor", label: "Floor", type: "number", list: true, required: true },
      { name: "number", label: "Flat no.", type: "text", list: true, required: true },
      { name: "bhk", label: "BHK", type: "number", list: true },
      { name: "area_sqft", label: "Area (sq ft)", type: "number", list: true },
      { name: "occupancy", label: "Occupancy", type: "select", options: ["owner", "tenant", "vacant"], list: true },
      { name: "owner_name", label: "Owner", type: "text", list: true },
      { name: "tenant_name", label: "Tenant", type: "text" },
      { name: "phone", label: "Phone", type: "text" },
      { name: "parking_slot", label: "Parking slot", type: "text", list: true },
    ],
  },
  {
    key: "buildings", label: "Buildings", icon: "🏗️", group: "Property", endpoint: "/buildings", write: ["secretary"],
    fields: [
      { name: "name", label: "Name", type: "text", list: true, required: true },
      { name: "floors", label: "Floors", type: "number", list: true },
      { name: "address", label: "Address", type: "text", list: true },
    ],
  },
  {
    key: "users", label: "Users & Roles", icon: "👥", group: "Property", endpoint: "/users", write: ["secretary"],
    read: C,
    fields: [
      { name: "name", label: "Name", type: "text", list: true, required: true },
      { name: "email", label: "Email", type: "text", list: true, required: true },
      { name: "phone", label: "Phone", type: "text", list: true },
      { name: "role", label: "Role", type: "select", list: true, required: true,
        options: ["resident", "secretary", "treasurer", "committee", "security", "staff", "vendor", "admin"] },
      { ...flat, required: false },
      { name: "resident_type", label: "Owner / Tenant", type: "select", options: ["owner", "tenant"] },
      { name: "family_members", label: "Family members", type: "textarea" },
      { name: "vehicles", label: "Vehicles", type: "text" },
      { name: "emergency_contact", label: "Emergency contact", type: "text" },
      { name: "password", label: "Password (set / reset)", type: "password", writeOnly: true },
      { name: "is_active", label: "Active", type: "checkbox", list: true },
    ],
  },
  {
    key: "vendors", label: "Vendors & AMC", icon: "🧰", group: "Operations", endpoint: "/vendors", write: ["secretary", "committee"],
    fields: [
      { name: "name", label: "Name", type: "text", list: true, required: true },
      { name: "category", label: "Category", type: "text", list: true },
      { name: "phone", label: "Phone", type: "text", list: true },
      { name: "email", label: "Email", type: "text" },
      { name: "contract_start", label: "Contract start", type: "date" },
      { name: "contract_end", label: "Contract end", type: "date", list: true },
      { name: "amount", label: "Contract value", type: "number", list: true },
      { name: "rating", label: "Rating (1-5)", type: "number", list: true },
      { name: "notes", label: "Notes", type: "textarea" },
    ],
  },
  {
    key: "assets", label: "Assets", icon: "⚙️", group: "Operations", endpoint: "/assets", write: ["secretary", "committee"],
    fields: [
      { name: "name", label: "Asset", type: "text", list: true, required: true },
      { name: "type", label: "Type", type: "text", list: true },
      { name: "location", label: "Location", type: "text", list: true },
      { name: "purchase_date", label: "Purchased", type: "date" },
      { name: "warranty_until", label: "Warranty until", type: "date", list: true },
      { name: "last_service", label: "Last service", type: "date" },
      { name: "next_service", label: "Next service", type: "date", list: true },
      vendor,
      { name: "notes", label: "Notes", type: "textarea" },
    ],
  },
  {
    key: "inventory", label: "Inventory", icon: "📦", group: "Operations", endpoint: "/inventory",
    read: [...C, "staff"], write: ["secretary", "committee", "staff"],
    fields: [
      { name: "item", label: "Item", type: "text", list: true, required: true },
      { name: "quantity", label: "Quantity", type: "number", list: true },
      { name: "min_quantity", label: "Min. stock", type: "number", list: true },
      { name: "unit", label: "Unit", type: "text", list: true },
      { name: "location", label: "Location", type: "text", list: true },
    ],
  },
  {
    key: "utility-readings", label: "Utilities", icon: "💧", group: "Operations", endpoint: "/utility-readings",
    read: [...C, "staff", "security"], write: ["secretary", "staff", "security"],
    fields: [
      { name: "type", label: "Type", type: "select", options: ["water", "electricity", "generator_fuel", "garbage"], list: true, required: true },
      { name: "date", label: "Date", type: "date", list: true },
      { name: "value", label: "Reading / quantity", type: "number", list: true },
      { name: "unit", label: "Unit", type: "text", list: true },
      { name: "notes", label: "Notes", type: "text", list: true },
    ],
  },
  {
    key: "staff", label: "Staff", icon: "🧑‍🔧", group: "Operations", endpoint: "/staff", read: [...C, "security"], write: ["secretary"],
    fields: [
      { name: "name", label: "Name", type: "text", list: true, required: true },
      { name: "role", label: "Role", type: "text", list: true },
      { name: "phone", label: "Phone", type: "text", list: true },
      { name: "shift", label: "Shift", type: "select", options: ["Day", "Night", "General"], list: true },
      { name: "salary", label: "Monthly salary", type: "number", list: true },
      { name: "joined_on", label: "Joined on", type: "date" },
      { name: "is_active", label: "Active", type: "checkbox", list: true },
    ],
  },
  {
    key: "staff-attendance", label: "Staff attendance", icon: "🕘", group: "Operations", endpoint: "/staff-attendance",
    read: [...C, "security"], write: ["secretary", "security"],
    fields: [
      { name: "staff_id", label: "Staff", type: "ref", ref: "/staff", list: true, required: true },
      { name: "date", label: "Date", type: "date", list: true },
      { name: "status", label: "Status", type: "select", options: ["present", "absent", "leave"], list: true },
      { name: "check_in", label: "In", type: "time", list: true },
      { name: "check_out", label: "Out", type: "time", list: true },
    ],
  },
  {
    key: "parking", label: "Parking", icon: "🅿️", group: "Operations", endpoint: "/parking",
    read: [...C, "security"], write: ["secretary", "security"],
    fields: [
      { name: "slot_no", label: "Slot", type: "text", list: true, required: true },
      { name: "type", label: "Type", type: "select", options: ["resident", "visitor", "reserved"], list: true },
      { ...flat },
      { name: "vehicle_no", label: "Vehicle no.", type: "text", list: true },
      { name: "sticker_no", label: "Sticker no.", type: "text", list: true },
    ],
  },
  {
    key: "expenses", label: "Expenses", icon: "🧾", group: "Finance", endpoint: "/expenses", read: C, write: ["secretary", "treasurer"],
    fields: [
      { name: "date", label: "Date", type: "date", list: true },
      { name: "category", label: "Category", type: "select", list: true,
        options: ["salary", "electricity", "maintenance", "repairs", "water", "insurance", "security", "other"] },
      { name: "description", label: "Description", type: "text", list: true },
      { name: "amount", label: "Amount (₹)", type: "number", list: true, money: true, required: true },
      vendor,
    ],
  },
  {
    key: "notices", label: "Notice board", icon: "📌", group: "Community", endpoint: "/notices", write: ["secretary", "committee"],
    fields: [
      { name: "title", label: "Title", type: "text", list: true, required: true },
      { name: "type", label: "Type", type: "select", options: ["general", "emergency", "event", "rule"], list: true },
      { name: "body", label: "Message", type: "textarea", required: true },
      { name: "created_at", label: "Posted", type: "text", list: true, readOnly: true },
    ],
  },
  {
    key: "meetings", label: "Meetings", icon: "🗓️", group: "Community", endpoint: "/meetings", write: ["secretary", "committee"],
    fields: [
      { name: "title", label: "Title", type: "text", list: true, required: true },
      { name: "type", label: "Type", type: "select", options: ["AGM", "Committee", "Special"], list: true },
      { name: "date", label: "Date", type: "date", list: true },
      { name: "location", label: "Location", type: "text", list: true },
      { name: "agenda", label: "Agenda", type: "textarea" },
      { name: "attendees", label: "Attendees", type: "textarea" },
      { name: "minutes", label: "Minutes of meeting", type: "textarea" },
      { name: "action_items", label: "Action items", type: "textarea" },
    ],
  },
  {
    key: "documents", label: "Documents", icon: "📁", group: "Community", endpoint: "/documents", write: ["secretary", "committee"],
    fields: [
      { name: "title", label: "Title", type: "text", list: true, required: true },
      { name: "category", label: "Category", type: "select", options: ["Legal", "Licence", "Insurance", "Audit", "Bylaws", "Other"], list: true },
      { name: "url", label: "Link", type: "text", list: true },
      { name: "expiry_date", label: "Expires on", type: "date", list: true },
      { name: "notes", label: "Notes", type: "textarea" },
    ],
  },
  {
    key: "emergency-contacts", label: "Emergency contacts", icon: "☎️", group: "Safety", endpoint: "/emergency-contacts", write: ["secretary"],
    fields: [
      { name: "name", label: "Name", type: "text", list: true, required: true },
      { name: "type", label: "Type", type: "text", list: true },
      { name: "phone", label: "Phone", type: "text", list: true, required: true },
      { name: "notes", label: "Notes", type: "text", list: true },
    ],
  },
  {
    key: "incidents", label: "Incidents", icon: "🚨", group: "Safety", endpoint: "/incidents",
    read: [...C, "security"], write: ["secretary", "committee", "security"],
    fields: [
      { name: "title", label: "Title", type: "text", list: true, required: true },
      { name: "type", label: "Type", type: "select", options: ["fire", "theft", "accident", "SOS", "other"], list: true },
      { name: "location", label: "Location", type: "text", list: true },
      { name: "description", label: "Description", type: "textarea" },
      { name: "status", label: "Status", type: "select", options: ["open", "investigating", "closed"], list: true },
      { name: "reported_on", label: "Reported", type: "text", list: true, readOnly: true },
    ],
  },
  {
    key: "audit", label: "Audit log", icon: "🔍", group: "Safety", endpoint: "/audit", read: C, readOnly: true,
    fields: [
      { name: "created_at", label: "When", type: "text", list: true },
      { name: "user_name", label: "Who", type: "text", list: true },
      { name: "action", label: "Action", type: "text", list: true },
      { name: "entity", label: "Entity", type: "text", list: true },
      { name: "entity_id", label: "ID", type: "text", list: true },
      { name: "detail", label: "Detail", type: "text", list: true },
    ],
  },
];
