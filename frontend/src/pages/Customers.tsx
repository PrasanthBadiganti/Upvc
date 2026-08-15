import { FormEvent, useEffect, useMemo, useState } from 'react';
import { BellRing, CalendarDays, Eye, FileText, Mail, MapPin, MoreVertical, Phone, Plus, ReceiptText, Search, Upload, UserPlus2, UsersRound, WalletCards } from 'lucide-react';
import { useSearchParams } from 'react-router-dom';
import api from '../api';
import { Button, Card, Field, Input, Loading, Modal, PageHeader, Select } from '../components/UI';
import ImportModal from '../components/ImportModal';
import MetricCard from '../components/MetricCard';
import Status from '../components/Status';
import { Customer, CustomerProfile } from '../types';
import { currency, INDIAN_STATES, shortDate, shortTime, toLocalInput } from '../utils';

const blank = {
  name: '',
  phone: '',
  email: '',
  address: '',
  gst_number: '',
  state: '',
  project_site: '',
  status: 'New',
  last_interaction: '',
  next_followup: '',
  quote_value: 0,
  pending_payment: 0,
  assigned_to: 'Arun Verma',
  notes: '',
};

const statuses = ['New', 'Quotation Sent', 'Negotiation', 'Live', 'Completed', 'Lost'];
const salespeople = ['Arun Verma', 'Neha Kapoor', 'Rohit Singh'];

export default function Customers() {
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [selected, setSelected] = useState<Customer | null>(null);
  const [profile, setProfile] = useState<CustomerProfile | null>(null);
  const [profileLoading, setProfileLoading] = useState(false);
  const [searchParams] = useSearchParams();
  const [search, setSearch] = useState(searchParams.get('q') || '');
  const [status, setStatus] = useState('');
  const [salesperson, setSalesperson] = useState('');
  const [open, setOpen] = useState(false);
  const [importOpen, setImportOpen] = useState(false);
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

  useEffect(() => {
    if (!selected) {
      setProfile(null);
      return;
    }
    let cancelled = false;
    setProfileLoading(true);
    api.get(`/customers/${selected.id}/profile`)
      .then(({ data }) => {
        if (!cancelled) {
          setProfile(data);
          setSelected(data.customer);
        }
      })
      .finally(() => {
        if (!cancelled) setProfileLoading(false);
      });
    return () => { cancelled = true; };
  }, [selected?.id]);

  const visibleCustomers = useMemo(
    () => customers.filter(c => !salesperson || c.assigned_to === salesperson),
    [customers, salesperson],
  );

  const counts = useMemo(() => ({
    new: visibleCustomers.filter(c => c.status === 'New').length,
    live: visibleCustomers.filter(c => ['Live', 'Completed'].includes(c.status)).length,
    pending: visibleCustomers.filter(c => ['Quotation Sent', 'Negotiation'].includes(c.status)).length,
    due: visibleCustomers.filter(c => c.next_followup).length,
  }), [visibleCustomers]);

  const activeCustomer = profile?.customer || selected;
  const metrics = profile?.metrics;

  const showAdd = () => {
    setEditing(null);
    setForm(blank);
    setOpen(true);
  };

  const showEdit = (customer: Customer) => {
    setEditing(customer);
    setForm({
      name: customer.name,
      phone: customer.phone,
      email: customer.email,
      address: customer.address,
      gst_number: customer.gst_number || '',
      state: customer.state || '',
      project_site: customer.project_site,
      status: customer.status,
      last_interaction: customer.last_interaction ? toLocalInput(customer.last_interaction) : '',
      next_followup: customer.next_followup ? toLocalInput(customer.next_followup) : '',
      quote_value: Number(customer.quote_value),
      pending_payment: Number(customer.pending_payment),
      assigned_to: customer.assigned_to,
      notes: customer.notes || '',
    });
    setOpen(true);
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!form.name || !form.state) {
      alert('Please fill in all required fields: Name and State');
      return;
    }
    const payload = {
      ...form,
      last_interaction: form.last_interaction || null,
      next_followup: form.next_followup || null,
    };
    if (editing) await api.put(`/customers/${editing.id}`, payload);
    else await api.post('/customers', payload);
    setOpen(false);
    await load();
  };

  return (
    <>
      <PageHeader title="Customers" subtitle="Lead and customer management" />
      <div className="customers-main-layout">
        <div className="customers-left-panel">
          <div className="metric-grid customers-metrics">
            <MetricCard label="New Enquiries" value={counts.new} change="Current list" icon={UserPlus2} tone="blue" />
            <MetricCard label="Live Customers" value={counts.live} change="Live + completed" icon={UsersRound} tone="teal" />
            <MetricCard label="Pending Quotations" value={counts.pending} change="Sent + negotiation" icon={FileText} tone="amber" />
            <MetricCard label="Follow-ups Due" value={counts.due} change="Scheduled follow-ups" icon={BellRing} tone="red" />
          </div>

          <div className="customers-layout">
        <Card className="customer-table-card">
          <div className="filters">
            <div className="search-box"><Search size={16} /><input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search customers by name, phone, email..." /></div>
            <Select value={status} onChange={e => setStatus(e.target.value)} style={{ width: 130 }}><option value="">All Status</option>{statuses.map(item => <option key={item}>{item}</option>)}</Select>
            <Select value={salesperson} onChange={e => setSalesperson(e.target.value)} style={{ width: 145 }}><option value="">All Salespersons</option>{salespeople.map(item => <option key={item}>{item}</option>)}</Select>
            <Button tone="secondary" onClick={() => setImportOpen(true)} style={{ marginLeft: 'auto' }}><Upload size={16} /> Import CSV</Button>
            <Button onClick={showAdd}><Plus size={16} /> Add Customer</Button>
          </div>

          {loading ? <Loading /> : (
            <div className="table-wrap"><table className="data-table"><thead><tr><th>Customer</th><th>Contact</th><th>Status</th><th>Assigned To</th><th style={{textAlign:'center'}}>Actions</th></tr></thead><tbody>
              {visibleCustomers.map(customer => <tr key={customer.id} className={selected?.id === customer.id ? 'selected-row' : ''} onClick={() => setSelected(customer)}>
                <td><span className="cell-title">{customer.name}</span><span className="cell-sub">{customer.code}</span></td>
                <td><span>{customer.phone}</span><span className="cell-sub">{customer.email}</span></td>
                <td><Status value={customer.status} /></td>
                <td>{customer.assigned_to}</td>
                <td style={{textAlign:'center'}}><div className="action-group"><button className="mini-button" onClick={e => { e.stopPropagation(); showEdit(customer); }}><MoreVertical size={14} /></button></div></td>
              </tr>)}
              {!visibleCustomers.length && <tr><td colSpan={5} className="muted">No customers found</td></tr>}
            </tbody></table></div>
          )}
          <div className="pagination"><span>Showing {visibleCustomers.length ? 1 : 0} to {visibleCustomers.length} of {visibleCustomers.length} customers</span><div className="pagination-controls"><button className="page-chip active">1</button></div><Select style={{ width: 95 }}><option>10 / page</option></Select></div>
        </Card>
          </div>
        </div>

        <Card className="customer-details">
          {activeCustomer ? (
            profileLoading && !profile ? <Loading /> : <>
              <div className="detail-title"><h3>{activeCustomer.name}</h3><Status value={activeCustomer.status} /></div>
              <div className="detail-section">
                <h4>Contact Information</h4>
                <div className="info-line"><Phone size={15} />{activeCustomer.phone || 'No phone'}</div>
                <div className="info-line"><Mail size={15} />{activeCustomer.email || 'No email'}</div>
                <div className="info-line"><MapPin size={15} />{activeCustomer.address || 'No address'}</div>
                <div className="info-line"><ReceiptText size={15} />GST: {activeCustomer.gst_number || 'Not provided'}</div>
                <div className="info-line"><MapPin size={15} />State: {activeCustomer.state || 'Not set'}</div>
              </div>

              <div className="detail-section">
                <h4>Project / Site</h4>
                <b style={{ fontSize: 13 }}>{activeCustomer.project_site || 'No project/site added'}</b>
                <div className="info-line"><UsersRound size={15} />Salesperson: {activeCustomer.assigned_to}</div>
              </div>

              <div className="detail-stat-grid">
                <div className="detail-stat"><span>Total Quotations</span><b>{metrics?.quotation_count ?? 0}</b></div>
                <div className="detail-stat"><span>Total Quote Value</span><b>{currency(metrics?.quotation_value || activeCustomer.quote_value)}</b></div>
                <div className="detail-stat"><span>Total Invoices</span><b>{metrics?.invoice_count ?? 0}</b></div>
                <div className="detail-stat"><span>Pending Amount</span><b>{currency(metrics?.pending_amount || activeCustomer.pending_payment)}</b></div>
              </div>

              <div className="detail-section">
                <h4>Next Follow-up</h4>
                <div className="info-line"><CalendarDays size={15} /><div>{shortDate(activeCustomer.next_followup)}, {shortTime(activeCustomer.next_followup)}<br /><span className="muted">{profile?.followups[0]?.purpose || 'No follow-up scheduled'}</span></div></div>
              </div>

              <div className="detail-section">
                <h4>Notes</h4>
                <p className="muted" style={{ fontSize: 12.5, lineHeight: 1.6 }}>{activeCustomer.notes || 'No notes added yet.'}</p>
              </div>

              <div className="detail-section">
                <h4>Collections</h4>
                <div className="info-line"><WalletCards size={15} />Paid: {currency(metrics?.paid_amount || 0)}</div>
                <div className="info-line"><WalletCards size={15} />Pending: {currency(metrics?.pending_amount || 0)}</div>
              </div>

              <div className="detail-section">
                <h4>Recent Timeline</h4>
                <div className="timeline">
                  {profile?.timeline.length ? profile.timeline.slice(0, 6).map(item => <div className="timeline-item" key={`${item.type}-${item.at}-${item.detail}`}><b>{shortDate(item.at)}, {shortTime(item.at)} - {item.title}</b><br />{item.detail}</div>) : <p className="muted" style={{ fontSize: 12.5 }}>No customer activity yet.</p>}
                </div>
              </div>
            </>
          ) : <div className="empty-state">Select a customer</div>}
        </Card>
      </div>

      <Modal open={open} onClose={() => setOpen(false)} title={editing ? 'Edit Customer' : 'Add Customer'} width={760}>
        <form onSubmit={submit}>
          <div className="form-grid">
            <Field label="Customer Name" required><Input required value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} /></Field>
            <Field label="Phone"><Input value={form.phone} onChange={e => setForm({ ...form, phone: e.target.value })} /></Field>
            <Field label="Email"><Input type="email" value={form.email} onChange={e => setForm({ ...form, email: e.target.value })} /></Field>
            <Field label="GST Number"><Input value={form.gst_number} onChange={e => setForm({ ...form, gst_number: e.target.value })} /></Field>
            <Field label="State" required><Select required value={form.state} onChange={e => setForm({ ...form, state: e.target.value })}><option value="">Select state...</option>{INDIAN_STATES.map(s => <option key={s}>{s}</option>)}</Select></Field>
            <Field label="Status"><Select value={form.status} onChange={e => setForm({ ...form, status: e.target.value })}>{statuses.map(item => <option key={item}>{item}</option>)}</Select></Field>
            <Field label="Project / Site"><Input value={form.project_site} onChange={e => setForm({ ...form, project_site: e.target.value })} /></Field>
            <Field label="Assigned To"><Select value={form.assigned_to} onChange={e => setForm({ ...form, assigned_to: e.target.value })}>{salespeople.map(item => <option key={item}>{item}</option>)}</Select></Field>
            <Field label="Next Follow-up"><Input type="datetime-local" value={form.next_followup} onChange={e => setForm({ ...form, next_followup: e.target.value })} /></Field>
            <Field label="Quote Value"><Input type="number" value={form.quote_value} onChange={e => setForm({ ...form, quote_value: Number(e.target.value) })} /></Field>
            <Field label="Pending Payment"><Input type="number" value={form.pending_payment} onChange={e => setForm({ ...form, pending_payment: Number(e.target.value) })} /></Field>
            <Field label="Address"><textarea className="input" value={form.address} onChange={e => setForm({ ...form, address: e.target.value })} /></Field>
            <Field label="Notes"><textarea className="input" value={form.notes} onChange={e => setForm({ ...form, notes: e.target.value })} /></Field>
          </div>
          <div className="form-actions"><Button type="button" tone="secondary" onClick={() => setOpen(false)}>Cancel</Button><Button type="submit">{editing ? 'Update' : 'Save'} Customer</Button></div>
        </form>
      </Modal>

      <ImportModal
        open={importOpen}
        onClose={() => setImportOpen(false)}
        title="Import Customers"
        previewUrl="/customers/import/preview"
        commitUrl="/customers/import/commit"
        columns={[{ key: 'name', label: 'Name' }, { key: 'phone', label: 'Phone' }, { key: 'email', label: 'Email' }, { key: 'gst_number', label: 'GSTIN' }, { key: 'project_site', label: 'Project/Site' }, { key: 'opening_balance', label: 'Opening Balance' }]}
        extraHelp="project_site, assigned_to, opening_balance"
        acceptTallyXml
        showAsOfDate
        onImported={() => load()}
      />
    </>
  );
}
