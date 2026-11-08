import { useEffect, useState } from "react";
import { api, fmtDate, money } from "../api.js";
import { useAuth } from "../auth.jsx";
import { Badge, Modal, statusTone } from "../components/Form.jsx";

export default function Billing() {
  const { can } = useAuth();
  const finance = can(["secretary", "treasurer", "committee"]);
  const canGenerate = can(["secretary", "treasurer"]);
  const [tab, setTab] = useState("bills");
  const [bills, setBills] = useState([]);
  const [status, setStatus] = useState("");
  const [defaulters, setDefaulters] = useState([]);
  const [report, setReport] = useState(null);
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");
  const [gen, setGen] = useState(null);
  const [receipt, setReceipt] = useState(null);

  const load = () => {
    api("/bills" + (status ? `?status=${status}` : "")).then(setBills).catch((e) => setError(e.message));
    if (finance) {
      api("/bills/defaulters").then(setDefaulters).catch(() => {});
      api("/bills/finance-report").then(setReport).catch(() => {});
    }
  };
  useEffect(load, [status]); // eslint-disable-line react-hooks/exhaustive-deps

  async function pay(b) {
    const mode = prompt(`Pay ${money(b.total)} for flat ${b.flat_number} (${b.month}).\nPayment mode (UPI / Card / NetBanking / Cash):`, "UPI");
    if (!mode) return;
    try {
      const r = await api(`/bills/${b.id}/pay`, { method: "POST", body: { payment_mode: mode } });
      setReceipt(r);
      load();
    } catch (e) { setError(e.message); }
  }

  async function generate(e) {
    e.preventDefault();
    try {
      const r = await api("/bills/generate", { method: "POST", body: { ...gen, rate: Number(gen.rate), fund_amount: Number(gen.fund_amount || 0) } });
      setInfo(`Generated ${r.created} bills (${r.skipped} already existed).`);
      setGen(null);
      load();
    } catch (err) { setError(err.message); }
  }

  async function lateFees() {
    const percent = prompt("Late fee as % of the base amount, applied to all overdue unpaid bills:", "2");
    if (!percent) return;
    try {
      const r = await api("/bills/apply-late-fees", { method: "POST", body: { percent: Number(percent) } });
      setInfo(`Late fee applied to ${r.updated} bills.`);
      load();
    } catch (err) { setError(err.message); }
  }

  const thisMonth = new Date().toISOString().slice(0, 7);

  return (
    <div>
      <div className="page-head">
        <h1>💳 Billing</h1>
        {canGenerate && (
          <div className="row">
            <button className="btn" onClick={lateFees}>Apply late fees</button>
            <button className="btn primary" onClick={() => setGen({ month: thisMonth, mode: "per_sqft", rate: 3, fund_amount: 300 })}>Generate monthly bills</button>
          </div>
        )}
      </div>
      {error && <div className="alert error" onClick={() => setError("")}>{error}</div>}
      {info && <div className="alert ok" onClick={() => setInfo("")}>{info}</div>}

      {finance && (
        <div className="tabs">
          {[["bills", "Bills"], ["defaulters", `Defaulters (${defaulters.length})`], ["report", "Income & expense"]].map(([k, l]) => (
            <button key={k} className={tab === k ? "active" : ""} onClick={() => setTab(k)}>{l}</button>
          ))}
        </div>
      )}

      {tab === "bills" && (
        <>
          <div className="row" style={{ marginBottom: 8 }}>
            <select value={status} onChange={(e) => setStatus(e.target.value)}>
              <option value="">All</option><option>pending</option><option>overdue</option><option>paid</option>
            </select>
          </div>
          <div className="card table-wrap">
            <table>
              <thead><tr><th>Month</th><th>Flat</th><th>Base</th><th>Fund</th><th>Late fee</th><th>Total</th><th>Due</th><th>Status</th><th></th></tr></thead>
              <tbody>
                {bills.map((b) => (
                  <tr key={b.id}>
                    <td>{b.month}</td><td>{b.flat_number}</td><td>{money(b.base_amount)}</td><td>{money(b.fund_amount)}</td>
                    <td>{b.late_fee ? money(b.late_fee) : "—"}</td><td><strong>{money(b.total)}</strong></td><td>{fmtDate(b.due_date)}</td>
                    <td><Badge tone={statusTone(b.status === "overdue" ? "overdue" : b.status)}>{b.status}</Badge></td>
                    <td className="actions">
                      {b.status !== "paid" && <button className="btn small primary" onClick={() => pay(b)}>Pay</button>}
                      {b.status === "paid" && <button className="btn small" onClick={() => setReceipt(b)}>Receipt</button>}
                    </td>
                  </tr>
                ))}
                {bills.length === 0 && <tr><td colSpan={9} className="empty">No bills.</td></tr>}
              </tbody>
            </table>
          </div>
        </>
      )}

      {tab === "defaulters" && (
        <div className="card table-wrap">
          <table>
            <thead><tr><th>Flat</th><th>Owner</th><th>Months due</th><th>Amount due</th></tr></thead>
            <tbody>
              {defaulters.map((d) => <tr key={d.flat_id}><td>{d.flat_number}</td><td>{d.owner_name || "—"}</td><td>{d.months_due}</td><td><strong>{money(d.amount_due)}</strong></td></tr>)}
              {defaulters.length === 0 && <tr><td colSpan={4} className="empty">No defaulters. 🎉</td></tr>}
            </tbody>
          </table>
        </div>
      )}

      {tab === "report" && report && (
        <div className="grid-2">
          <div className="card">
            <h3>Summary</h3>
            <div className="list-row"><span>Total income collected</span><strong>{money(report.total_income)}</strong></div>
            <div className="list-row"><span>Total expenses</span><strong>{money(report.total_expense)}</strong></div>
            <div className="list-row"><span>Net balance</span><strong>{money(report.total_income - report.total_expense)}</strong></div>
            <div className="list-row"><span>Pending dues</span><strong>{money(report.pending_dues)}</strong></div>
            <h3 style={{ marginTop: 16 }}>Expenses by category</h3>
            {report.expense_by_category.map((c) => <div key={c.category} className="list-row"><span>{c.category}</span><span>{money(c.amount)}</span></div>)}
          </div>
          <div className="card table-wrap">
            <h3>By month</h3>
            <table>
              <thead><tr><th>Month</th><th>Income</th><th>Expense</th><th>Net</th></tr></thead>
              <tbody>{report.months.map((m) => <tr key={m.month}><td>{m.month}</td><td>{money(m.income)}</td><td>{money(m.expense)}</td><td>{money(m.net)}</td></tr>)}</tbody>
            </table>
          </div>
        </div>
      )}

      {gen && (
        <Modal title="Generate monthly bills" onClose={() => setGen(null)}>
          <form onSubmit={generate}>
            <div className="form-grid">
              <label className="field"><span>Month</span><input type="month" value={gen.month} onChange={(e) => setGen({ ...gen, month: e.target.value })} required /></label>
              <label className="field"><span>Mode</span>
                <select value={gen.mode} onChange={(e) => setGen({ ...gen, mode: e.target.value })}>
                  <option value="per_sqft">Rate per sq ft</option><option value="fixed">Fixed per flat</option>
                </select></label>
              <label className="field"><span>{gen.mode === "per_sqft" ? "Rate (₹ / sq ft)" : "Amount (₹)"}</span><input type="number" step="any" value={gen.rate} onChange={(e) => setGen({ ...gen, rate: e.target.value })} required /></label>
              <label className="field"><span>Sinking / repair fund (₹)</span><input type="number" value={gen.fund_amount} onChange={(e) => setGen({ ...gen, fund_amount: e.target.value })} /></label>
              <label className="field"><span>Due date (blank = 10th)</span><input type="date" value={gen.due_date || ""} onChange={(e) => setGen({ ...gen, due_date: e.target.value })} /></label>
            </div>
            <div className="modal-foot"><button type="button" className="btn" onClick={() => setGen(null)}>Cancel</button><button className="btn primary">Generate</button></div>
          </form>
        </Modal>
      )}

      {receipt && (
        <Modal title="Payment receipt" onClose={() => setReceipt(null)}>
          <div className="receipt">
            <div className="list-row"><span>Receipt no.</span><strong>{receipt.receipt_no}</strong></div>
            <div className="list-row"><span>Flat</span><span>{receipt.flat_number}</span></div>
            <div className="list-row"><span>Month</span><span>{receipt.month}</span></div>
            <div className="list-row"><span>Amount</span><strong>{money(receipt.total)}</strong></div>
            <div className="list-row"><span>Paid on</span><span>{fmtDate(receipt.paid_on)}</span></div>
            <div className="list-row"><span>Mode</span><span>{receipt.payment_mode}</span></div>
          </div>
          <div className="modal-foot"><button className="btn" onClick={() => window.print()}>Print</button><button className="btn primary" onClick={() => setReceipt(null)}>Close</button></div>
        </Modal>
      )}
    </div>
  );
}
