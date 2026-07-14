import { FormEvent, useEffect, useMemo, useState } from 'react';
import { CalendarDays, Eye, Mail, MapPin, MoreVertical, Phone, Plus, Search, UserPlus2, UsersRound, FileText, BellRing } from 'lucide-react';
import api from '../api';
import { Button, Card, Field, Input, Loading, Modal, PageHeader, Select } from '../components/UI';
import MetricCard from '../components/MetricCard';
import Status from '../components/Status';
import { Customer } from '../types';
import { currency, shortDate, shortTime, toLocalInput } from '../utils';

const blank = {
  name: '', phone: '', email: '', address: '', project_site: '', status: 'New',
  last_interaction: '', next_followup: '', quote_value: 0, pending_payment: 0, assigned_to: 'Arun Verma'
};

export default function Customers() {
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [selected, setSelected] = useState<Customer | null>(null);
  const [search, setSearch] = useState('');
  const [status, setStatus] = useState('');
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<Customer | null>(null);
  const [form, setForm] = useState(blank);
  const [loading, setLoading] = useState(true);
  const load = async () => {
    setLoading(true);
    const { data } = await api.get('/customers', { params: { search, status } });
    setCustomers(data);
    setSelected(prev => prev ? data.find((c: Customer) => c.id === prev.id) || data[0] || null : data[0] || null);
    setLoading(false);
  };
  useEffect(() => { load(); }, [search, status]);

  const counts = useMemo(() => ({
    new: customers.filter(c => c.status === 'New').length,
    live: customers.filter(c => ['Live','Completed'].includes(c.status)).length,
    pending: customers.filter(c => ['Quotation Sent','Negotiation'].includes(c.status)).length,
    due: customers.filter(c => c.next_followup).length,
  }), [customers]);

  const showAdd = () => { setEditing(null); setForm(blank); setOpen(true); };
  const showEdit = (c: Customer) => {
    setEditing(c);
    setForm({
      name:c.name, phone:c.phone, email:c.email, address:c.address, project_site:c.project_site, status:c.status,
      last_interaction:c.last_interaction ? toLocalInput(c.last_interaction) : '', next_followup:c.next_followup ? toLocalInput(c.next_followup) : '',
      quote_value:Number(c.quote_value), pending_payment:Number(c.pending_payment), assigned_to:c.assigned_to
    });
    setOpen(true);
  };
  const submit = async (e: FormEvent) => {
    e.preventDefault();
    const payload = { ...form, last_interaction: form.last_interaction || null, next_followup: form.next_followup || null };
    if (editing) await api.put(`/customers/${editing.id}`, payload); else await api.post('/customers', payload);
    setOpen(false); await load();
  };

  return (
    <>
      <PageHeader title="Customers" subtitle="Lead and customer management" />
      <div className="metric-grid customers-metrics">
        <MetricCard label="New Enquiries" value={counts.new || 42} change="18% vs Apr 2025" icon={UserPlus2} tone="blue" />
        <MetricCard label="Live Customers" value={counts.live || 342} change="8% vs Apr 2025" icon={UsersRound} tone="teal" />
        <MetricCard label="Pending Quotations" value={counts.pending || 75} change="15% vs Apr 2025" icon={FileText} tone="amber" />
        <MetricCard label="Follow-ups Due" value={counts.due || 31} change="6% vs Apr 2025" icon={BellRing} tone="red" />
      </div>
      <div className="customers-layout">
        <Card className="customer-table-card">
          <div className="filters">
            <div className="search-box"><Search size={16}/><input value={search} onChange={e=>setSearch(e.target.value)} placeholder="Search customers by name, phone, email..." /></div>
            <Select value={status} onChange={e=>setStatus(e.target.value)} style={{width:130}}><option value="">All Status</option><option>New</option><option>Quotation Sent</option><option>Negotiation</option><option>Live</option><option>Completed</option><option>Lost</option></Select>
            <Select style={{width:145}}><option>All Salespersons</option><option>Arun Verma</option><option>Neha Kapoor</option><option>Rohit Singh</option></Select>
            <Button onClick={showAdd} style={{marginLeft:'auto'}}><Plus size={16}/> Add Customer</Button>
          </div>
          {loading ? <Loading/> : <div className="table-wrap"><table className="data-table"><thead><tr><th>Customer</th><th>Contact</th><th>Project / Site</th><th>Status</th><th>Last Interaction</th><th>Next Follow-up</th><th>Quote Value</th><th>Pending Payment</th><th>Assigned To</th><th>Actions</th></tr></thead><tbody>
            {customers.map(c => <tr key={c.id} className={selected?.id===c.id?'selected-row':''} onClick={()=>setSelected(c)}>
              <td><span className="cell-title">{c.name}</span><span className="cell-sub">{c.code}</span></td>
              <td><span>{c.phone}</span><span className="cell-sub">{c.email}</span></td>
              <td>{c.project_site}</td><td><Status value={c.status}/></td>
              <td>{shortDate(c.last_interaction)}<span className="cell-sub">{shortTime(c.last_interaction)}</span></td>
              <td style={{color:'#1561ec'}}>{shortDate(c.next_followup)}<span className="cell-sub" style={{color:'#1561ec'}}>{shortTime(c.next_followup)}</span></td>
              <td className="amount">{currency(c.quote_value)}</td><td className={`amount ${Number(c.pending_payment)>0?'danger':'success'}`}>{currency(c.pending_payment)}</td>
              <td>{c.assigned_to}</td><td><div className="action-group"><button className="mini-button" onClick={e=>{e.stopPropagation();setSelected(c)}}><Eye size={14}/></button><button className="mini-button" onClick={e=>{e.stopPropagation();showEdit(c)}}><MoreVertical size={14}/></button></div></td>
            </tr>)}
          </tbody></table></div>}
          <div className="pagination"><span>Showing 1 to {customers.length} of {customers.length} customers</span><div className="pagination-controls"><button className="page-chip active">1</button><button className="page-chip">2</button><button className="page-chip">3</button><button className="page-chip">4</button><button className="page-chip">5</button></div><Select style={{width:95}}><option>10 / page</option></Select></div>
        </Card>

        <Card className="customer-details">
          {selected ? <>
            <div className="detail-title"><h3>{selected.name}</h3><Status value={selected.status}/></div>
            <div className="detail-section"><h4>Contact Information</h4><div className="info-line"><Phone size={15}/>{selected.phone}</div><div className="info-line"><Mail size={15}/>{selected.email}</div><div className="info-line"><MapPin size={15}/>{selected.address}</div></div>
            <div className="detail-section"><h4>Project / Site</h4><b style={{fontSize:11}}>{selected.project_site}</b><div className="info-line"><MapPin size={15}/>Project location and installation site</div></div>
            <div className="detail-stat-grid"><div className="detail-stat"><span>Total Quotations</span><b>6</b></div><div className="detail-stat"><span>Total Quote Value</span><b>{currency(selected.quote_value)}</b></div><div className="detail-stat"><span>Invoice Balance</span><b>{currency(selected.pending_payment)}</b></div><div className="detail-stat"><span>Total Invoices</span><b>4</b></div></div>
            <div className="detail-section"><h4>Next Follow-up</h4><div className="info-line"><CalendarDays size={15}/><div>{shortDate(selected.next_followup)}, {shortTime(selected.next_followup)}<br/><span className="muted">Discuss final specifications and pricing</span></div></div></div>
            <div className="detail-section"><h4>Last Notes</h4><p className="muted" style={{fontSize:10,lineHeight:1.6}}>Shared revised quotation with toughened glass option. Awaiting feedback.</p></div>
            <div className="detail-section"><h4>Recent Follow-ups</h4><div className="timeline"><div className="timeline-item"><b>30 Apr 2025, 10:30 AM</b><br/>Shared revised quotation with toughened glass option.</div><div className="timeline-item"><b>28 Apr 2025, 04:00 PM</b><br/>Discussed budget and customization.</div><div className="timeline-item"><b>25 Apr 2025, 11:20 AM</b><br/>Sent product brochure and past projects.</div></div></div>
          </> : <div className="empty-state">Select a customer</div>}
        </Card>
      </div>

      <Modal open={open} onClose={()=>setOpen(false)} title={editing?'Edit Customer':'Add Customer'} width={700}>
        <form onSubmit={submit}>
          <div className="form-grid">
            <Field label="Customer Name" required><Input required value={form.name} onChange={e=>setForm({...form,name:e.target.value})}/></Field>
            <Field label="Phone"><Input value={form.phone} onChange={e=>setForm({...form,phone:e.target.value})}/></Field>
            <Field label="Email"><Input type="email" value={form.email} onChange={e=>setForm({...form,email:e.target.value})}/></Field>
            <Field label="Status"><Select value={form.status} onChange={e=>setForm({...form,status:e.target.value})}><option>New</option><option>Quotation Sent</option><option>Negotiation</option><option>Live</option><option>Completed</option><option>Lost</option></Select></Field>
            <Field label="Project / Site"><Input value={form.project_site} onChange={e=>setForm({...form,project_site:e.target.value})}/></Field>
            <Field label="Assigned To"><Select value={form.assigned_to} onChange={e=>setForm({...form,assigned_to:e.target.value})}><option>Arun Verma</option><option>Neha Kapoor</option><option>Rohit Singh</option></Select></Field>
            <Field label="Next Follow-up"><Input type="datetime-local" value={form.next_followup} onChange={e=>setForm({...form,next_followup:e.target.value})}/></Field>
            <Field label="Quote Value"><Input type="number" value={form.quote_value} onChange={e=>setForm({...form,quote_value:Number(e.target.value)})}/></Field>
            <Field label="Pending Payment"><Input type="number" value={form.pending_payment} onChange={e=>setForm({...form,pending_payment:Number(e.target.value)})}/></Field>
            <Field label="Address"><textarea className="input" value={form.address} onChange={e=>setForm({...form,address:e.target.value})}/></Field>
          </div>
          <div className="form-actions"><Button type="button" tone="secondary" onClick={()=>setOpen(false)}>Cancel</Button><Button type="submit">{editing?'Update':'Save'} Customer</Button></div>
        </form>
      </Modal>
    </>
  );
}
