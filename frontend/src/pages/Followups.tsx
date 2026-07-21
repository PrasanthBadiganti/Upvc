import { FormEvent, useEffect, useMemo, useState } from 'react';
import { CalendarClock, CheckCircle2, IndianRupee, MessageCircle, Phone, Plus, TimerReset, WalletCards } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import api from '../api';
import { Button, Card, Field, Input, Loading, Modal, PageHeader, Select } from '../components/UI';
import MetricCard from '../components/MetricCard';
import Status from '../components/Status';
import { Customer, Followup, Invoice } from '../types';
import { currency, shortDate, shortTime, toLocalInput } from '../utils';

const digitsOnly = (phone: string) => phone.replace(/\D/g, '');
const waLink = (phone: string) => `https://wa.me/${digitsOnly(phone)}`;

const startOfWeek = () => { const d = new Date(); const day = d.getDay(); const diff = day === 0 ? 6 : day - 1; d.setDate(d.getDate() - diff); d.setHours(0, 0, 0, 0); return d; };

export default function Followups() {
  const navigate = useNavigate();
  const [followups, setFollowups] = useState<Followup[]>([]);
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState('Today');
  const [stageFilter, setStageFilter] = useState('');
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ customer_id: 0, scheduled_at: toLocalInput(), purpose: 'Payment Reminder', assigned_to: 'Arun Verma', priority: 'Medium', channel: 'Call', status: 'Today', next_reminder: '', notes: '' });

  const load = async () => {
    setLoading(true);
    const [a, b, c] = await Promise.all([api.get('/followups'), api.get('/invoices'), api.get('/customers')]);
    setFollowups(a.data); setInvoices(b.data); setCustomers(c.data);
    if (c.data[0]) setForm(f => ({ ...f, customer_id: f.customer_id || c.data[0].id }));
    setLoading(false);
  };
  useEffect(() => { load(); }, []);

  const groups = useMemo(() => ({
    Today: followups.filter(f => f.status === 'Today' || new Date(f.scheduled_at).toDateString() === new Date().toDateString()),
    Upcoming: followups.filter(f => f.status === 'Upcoming'),
    Overdue: followups.filter(f => f.status === 'Overdue'),
    Completed: followups.filter(f => f.status === 'Completed'),
  }), [followups]);

  const pending = invoices.reduce((s, i) => s + Number(i.pending_balance), 0);
  const pendingInvoiceCount = invoices.filter(i => Number(i.pending_balance) > 0).length;

  const collectedThisWeek = useMemo(() => {
    const weekStart = startOfWeek();
    let total = 0, count = 0;
    for (const inv of invoices) for (const p of inv.payments) {
      if (new Date(p.payment_date) >= weekStart) { total += Number(p.amount); count += 1; }
    }
    return { total, count };
  }, [invoices]);

  const recentActivity = useMemo(() => {
    type Item = { icon: 'call' | 'payment'; title: string; detail: string; at: string };
    const items: Item[] = [];
    for (const f of followups) if (f.status === 'Completed') items.push({ icon: 'call', title: `${f.channel} completed`, detail: `${f.purpose} — ${f.customer.name}`, at: f.scheduled_at });
    for (const inv of invoices) for (const p of inv.payments) items.push({ icon: 'payment', title: 'Payment Received', detail: `Rs. ${Number(p.amount).toLocaleString('en-IN')} from ${inv.customer.name}`, at: p.payment_date });
    return items.sort((a, b) => new Date(b.at).getTime() - new Date(a.at).getTime()).slice(0, 5);
  }, [followups, invoices]);

  const trackerRows = useMemo(() => {
    return invoices.filter(i => {
      if (!stageFilter) return true;
      const stage = new Date(i.due_date) < new Date() ? 'Overdue' : Number(i.pending_balance) <= 0 ? 'Paid' : 'Due Soon';
      return stage === stageFilter;
    });
  }, [invoices, stageFilter]);

  const submit = async (e: FormEvent) => { e.preventDefault(); await api.post('/followups', { ...form, next_reminder: form.next_reminder || null }); setOpen(false); await load(); };
  const complete = async (f: Followup) => { await api.put(`/followups/${f.id}`, { customer_id: f.customer_id, scheduled_at: f.scheduled_at, purpose: f.purpose, assigned_to: f.assigned_to, priority: f.priority, channel: f.channel, status: 'Completed', next_reminder: f.next_reminder, notes: f.notes }); await load(); };

  return <>
    <PageHeader title="Follow-ups & Collections" subtitle="Manage customer follow-ups and track payments" action={<Button onClick={() => setOpen(true)}><Plus size={15} /> Add Follow-up</Button>} />
    <div className="metric-grid followup-metrics">
      <MetricCard label="Due Today" value={groups.Today.length} change={`${groups.Today.filter(f => f.priority === 'High').length} high priority`} icon={CalendarClock} tone="blue" />
      <MetricCard label="Overdue Follow-ups" value={groups.Overdue.length} change={`${groups.Overdue.filter(f => f.priority === 'High').length} high priority`} icon={TimerReset} tone="red" />
      <MetricCard label="Pending Amount" value={currency(pending)} change={`Across ${pendingInvoiceCount} invoice${pendingInvoiceCount === 1 ? '' : 's'}`} icon={IndianRupee} tone="amber" />
      <MetricCard label="Collected This Week" value={currency(collectedThisWeek.total)} change={`${collectedThisWeek.count} payment${collectedThisWeek.count === 1 ? '' : 's'}`} icon={CheckCircle2} tone="green" />
    </div>
    {loading ? <Loading /> : <>
      <div className="followups-main">
        <Card className="followups-list-card">
          <div className="card-head"><h3>Follow-up Management</h3></div>
          <div className="follow-tabs">{Object.entries(groups).map(([name, list]) => <button className={tab === name ? 'active' : ''} onClick={() => setTab(name)} key={name}>{name} ({list.length})</button>)}</div>
          {groups[tab as keyof typeof groups].map(f => <div className={`follow-card ${f.priority.toLowerCase()}`} key={f.id}>
            <div className="follow-time">{shortTime(f.scheduled_at)}<small>{new Date(f.scheduled_at).getHours() < 12 ? 'AM' : 'PM'}</small></div>
            <div className="follow-copy"><b>{f.customer.name}</b><p>Purpose: {f.purpose}</p><p>Assigned to: {f.assigned_to}</p></div>
            <div className="follow-actions">
              <Status value={f.priority} />
              <a className="follow-action" href={`tel:${f.customer.phone}`}><Phone size={13} /> Call</a>
              <a className="follow-action" href={waLink(f.customer.phone)} target="_blank" rel="noreferrer"><MessageCircle size={13} /> {f.channel}</a>
              {f.status !== 'Completed' && <button className="follow-action" onClick={() => complete(f)}><CheckCircle2 size={13} /> Done</button>}
              <small className="muted" style={{ width: '100%', textAlign: 'right' }}>Next Reminder: {shortTime(f.next_reminder)}</small>
            </div>
          </div>)}
          {!groups[tab as keyof typeof groups].length && <div className="muted" style={{ padding: '16px 0' }}>No {tab.toLowerCase()} follow-ups</div>}
        </Card>
        <div>
          <Card className="collection-card">
            <div className="card-head"><h3>Pending Payments / Collection Tracker</h3>
              <Select style={{ width: 130 }} value={stageFilter} onChange={e => setStageFilter(e.target.value)}>
                <option value="">All Stages</option><option>Overdue</option><option>Due Soon</option><option>Paid</option>
              </Select>
            </div>
            <div className="table-wrap"><table className="data-table"><thead><tr><th>Customer</th><th>Invoice No.</th><th>Stage</th><th>Due Date</th><th>Pending Amount</th><th>Reminder Status</th><th>Actions</th></tr></thead><tbody>
              {trackerRows.map(i => <tr key={i.id}>
                <td>{i.customer.name}</td>
                <td>{i.number}</td>
                <td><Status value={new Date(i.due_date) < new Date() ? 'Overdue' : Number(i.pending_balance) <= 0 ? 'Paid' : 'Due Soon'} /></td>
                <td>{shortDate(i.due_date)}</td>
                <td className="amount">{currency(i.pending_balance)}</td>
                <td><Status value={Number(i.pending_balance) > 0 ? 'Reminder Sent' : 'Paid'} /></td>
                <td><div className="action-group">
                  <a className="mini-button" href={`tel:${i.customer.phone}`}><Phone size={14} /></a>
                  <a className="mini-button" href={waLink(i.customer.phone)} target="_blank" rel="noreferrer"><MessageCircle size={14} /></a>
                  <button className="mini-button" onClick={() => navigate(`/invoices/${i.id}`)}><IndianRupee size={14} /></button>
                </div></td>
              </tr>)}
              {!trackerRows.length && <tr><td colSpan={7} className="muted">No invoices match this stage</td></tr>}
            </tbody></table></div>
            <div className="panel-total"><button className="link-button" onClick={() => navigate('/invoices')}>View All Pending Payments</button><span>Total Pending: {currency(pending)}</span></div>
          </Card>
          <Card className="activity-strip">
            <div className="card-head"><h3>Recent Activity & Notes</h3></div>
            <div className="activity-horizontal">
              {recentActivity.map((a, i) => <div className="activity-mini" key={i}><div className="activity-icon">{a.icon === 'payment' ? <WalletCards size={15} /> : <Phone size={15} />}</div><b>{a.title}</b><p>{a.detail}<br />{shortDate(a.at)}</p></div>)}
              {!recentActivity.length && <div className="muted">No recent activity yet</div>}
            </div>
          </Card>
        </div>
      </div>
    </>}
    <Modal open={open} onClose={() => setOpen(false)} title="Add Follow-up" width={650}>
      <form onSubmit={submit}>
        <div className="form-grid">
          <Field label="Customer"><Select value={form.customer_id} onChange={e => setForm({ ...form, customer_id: Number(e.target.value) })}>{customers.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}</Select></Field>
          <Field label="Scheduled At"><Input type="datetime-local" value={form.scheduled_at} onChange={e => setForm({ ...form, scheduled_at: e.target.value })} /></Field>
          <Field label="Purpose"><Input value={form.purpose} onChange={e => setForm({ ...form, purpose: e.target.value })} /></Field>
          <Field label="Assigned To"><Select value={form.assigned_to} onChange={e => setForm({ ...form, assigned_to: e.target.value })}><option>Arun Verma</option><option>Neha Kapoor</option><option>Rohit Singh</option></Select></Field>
          <Field label="Priority"><Select value={form.priority} onChange={e => setForm({ ...form, priority: e.target.value })}><option>Low</option><option>Medium</option><option>High</option></Select></Field>
          <Field label="Channel"><Select value={form.channel} onChange={e => setForm({ ...form, channel: e.target.value })}><option>Call</option><option>WhatsApp</option><option>Visit</option><option>Email</option></Select></Field>
          <Field label="Status"><Select value={form.status} onChange={e => setForm({ ...form, status: e.target.value })}><option>Today</option><option>Upcoming</option><option>Overdue</option><option>Completed</option></Select></Field>
          <Field label="Next Reminder"><Input type="datetime-local" value={form.next_reminder} onChange={e => setForm({ ...form, next_reminder: e.target.value })} /></Field>
        </div>
        <div className="form-actions"><Button type="button" tone="secondary" onClick={() => setOpen(false)}>Cancel</Button><Button type="submit">Save Follow-up</Button></div>
      </form>
    </Modal>
  </>;
}
