import { FormEvent, useEffect, useState } from 'react';
import { Building2, Edit3, Search, Upload, UserPlus2 } from 'lucide-react';
import api from '../api';
import { Button, Card, Field, Input, Loading, Modal, PageHeader, Select } from '../components/UI';
import ImportModal from '../components/ImportModal';
import Status from '../components/Status';
import { Vendor } from '../types';
import { currency, INDIAN_STATES } from '../utils';
import Pagination, { usePagination } from '../components/Pagination';

type VendorForm = Omit<Vendor, 'id' | 'code' | 'created_at'>;

const blank: VendorForm = {
  name: '',
  phone: '',
  email: '',
  address: '',
  gst_number: '',
  state: '',
  status: 'Active',
  pending_payment: 0,
  notes: '',
};

export default function Vendors() {
  const [vendors, setVendors] = useState<Vendor[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [status, setStatus] = useState('');
  const [open, setOpen] = useState(false);
  const [importOpen, setImportOpen] = useState(false);
  const [editing, setEditing] = useState<Vendor | null>(null);
  const [form, setForm] = useState<VendorForm>(blank);

  const load = async () => {
    setLoading(true);
    const { data } = await api.get('/vendors', { params: { search, status } });
    setVendors(data);
    setLoading(false);
  };

  useEffect(() => { load(); }, [search, status]);

  const showAdd = () => {
    setEditing(null);
    setForm(blank);
    setOpen(true);
  };

  const showEdit = (vendor: Vendor) => {
    setEditing(vendor);
    setForm({
      name: vendor.name,
      phone: vendor.phone,
      email: vendor.email,
      address: vendor.address,
      gst_number: vendor.gst_number || '',
      state: vendor.state || '',
      status: vendor.status,
      pending_payment: Number(vendor.pending_payment),
      notes: vendor.notes || '',
    });
    setOpen(true);
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (editing) await api.put(`/vendors/${editing.id}`, form);
    else await api.post('/vendors', form);
    setOpen(false);
    await load();
  };

  const { pageRows, props: pageProps } = usePagination(vendors);

  return <>
    <PageHeader title="Vendors" subtitle="Suppliers you buy raw material and hardware from"  toolbar={<><div className="search-box"><Search size={16} /><input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search vendor by name, phone, email..." /></div>
      <Select value={status} onChange={e => setStatus(e.target.value)} style={{ width: 130 }}><option value="">All Status</option><option>Active</option><option>Inactive</option></Select>
      <Button tone="secondary" onClick={() => setImportOpen(true)}><Upload size={16} /> Import CSV</Button>
      <Button onClick={showAdd}><UserPlus2 size={16} /> Add Vendor</Button></>}/>
        <Card className="list-card">{loading ? <Loading /> : <div className="table-wrap"><table className="data-table"><thead><tr><th>Vendor ID</th><th>Vendor Name</th><th>Mobile</th><th>Email</th><th>GSTIN</th><th>State</th><th>Pending Payable</th><th>Status</th><th>Action</th></tr></thead><tbody>{pageRows.map(vendor => <tr key={vendor.id}>
      <td className="nowrap">{vendor.code}</td><td title={vendor.name}><b>{vendor.name}</b></td>
      <td className="nowrap">{vendor.phone || <span className="muted">--</span>}</td><td title={vendor.email}>{vendor.email || <span className="muted">--</span>}</td>
      <td>{vendor.gst_number || '--'}</td>
      <td>{vendor.state || '--'}</td>
      <td className={`amount ${Number(vendor.pending_payment) > 0 ? 'danger' : 'success'}`}>{currency(vendor.pending_payment, 2)}</td>
      <td><Status value={vendor.status} /></td>
      <td><button className="mini-button" onClick={() => showEdit(vendor)}><Edit3 size={14} /></button></td>
    </tr>)}
    {!vendors.length && <tr><td colSpan={9} className="muted">No vendors found</td></tr>}
    </tbody></table></div>}<Pagination {...pageProps} noun="vendors" /></Card>

    <Modal open={open} onClose={() => setOpen(false)} title={editing ? 'Edit Vendor' : 'Add Vendor'} width={720}>
      <form onSubmit={submit}>
        <div className="form-grid">
          <Field label="Vendor Name" required><Input required value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} /></Field>
          <Field label="Phone"><Input value={form.phone} onChange={e => setForm({ ...form, phone: e.target.value })} /></Field>
          <Field label="Email"><Input type="email" value={form.email} onChange={e => setForm({ ...form, email: e.target.value })} /></Field>
          <Field label="GST Number"><Input value={form.gst_number} onChange={e => setForm({ ...form, gst_number: e.target.value })} /></Field>
          <Field label="State"><Select value={form.state} onChange={e => setForm({ ...form, state: e.target.value })}><option value="">Select state</option>{INDIAN_STATES.map(s => <option key={s}>{s}</option>)}</Select></Field>
          <Field label="Status"><Select value={form.status} onChange={e => setForm({ ...form, status: e.target.value })}><option>Active</option><option>Inactive</option></Select></Field>
          <Field label="Address"><textarea className="input" value={form.address} onChange={e => setForm({ ...form, address: e.target.value })} /></Field>
          <Field label="Notes"><textarea className="input" value={form.notes} onChange={e => setForm({ ...form, notes: e.target.value })} /></Field>
        </div>
        <div className="form-actions"><Button type="button" tone="secondary" onClick={() => setOpen(false)}>Cancel</Button><Button type="submit"><Building2 size={14} /> {editing ? 'Update' : 'Save'} Vendor</Button></div>
      </form>
    </Modal>

    <ImportModal
      open={importOpen}
      onClose={() => setImportOpen(false)}
      title="Import Vendors"
      previewUrl="/vendors/import/preview"
      commitUrl="/vendors/import/commit"
      columns={[{ key: 'name', label: 'Name' }, { key: 'phone', label: 'Phone' }, { key: 'email', label: 'Email' }, { key: 'gst_number', label: 'GSTIN' }, { key: 'address', label: 'Address' }, { key: 'opening_balance', label: 'Opening Balance' }]}
      extraHelp="opening_balance"
      acceptTallyXml
      showAsOfDate
      onImported={() => load()}
    />
  </>;
}