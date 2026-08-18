import { FormEvent, useEffect, useState } from 'react';
import { Boxes, Eye, Search } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import api from '../api';
import { Button, Card, Field, Input, Loading, Modal, PageHeader, Select } from '../components/UI';
import Status from '../components/Status';
import { FixedAsset, Vendor } from '../types';
import { currency, shortDate } from '../utils';
import Pagination, { usePagination } from '../components/Pagination';

const categories = ['Machinery', 'Vehicle', 'Furniture', 'Computer & IT Equipment', 'Office Equipment', 'Building', 'Tools', 'Other'];

type AssetForm = {
  name: string;
  category: string;
  purchase_date: string;
  purchase_cost: number;
  salvage_value: number;
  useful_life_years: number;
  depreciation_method: string;
  depreciation_rate: number | '';
  vendor_id: number | '';
  payment_mode: string;
  location: string;
  notes: string;
};

const blank: AssetForm = {
  name: '',
  category: 'Other',
  purchase_date: new Date().toISOString().slice(0, 10),
  purchase_cost: 0,
  salvage_value: 0,
  useful_life_years: 5,
  depreciation_method: 'Straight Line',
  depreciation_rate: '',
  vendor_id: '',
  payment_mode: 'Bank',
  location: '',
  notes: '',
};

export default function FixedAssets() {
  const navigate = useNavigate();
  const [assets, setAssets] = useState<FixedAsset[]>([]);
  const [vendors, setVendors] = useState<Vendor[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState<AssetForm>(blank);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);

  const load = () => { setLoading(true); api.get('/fixed-assets').then(r => setAssets(r.data)).finally(() => setLoading(false)); };
  useEffect(() => { load(); api.get('/vendors').then(r => setVendors(r.data)); }, []);

  const filtered = assets.filter(a => `${a.code} ${a.name} ${a.category}`.toLowerCase().includes(search.toLowerCase()));

  const showAdd = () => { setForm(blank); setError(''); setOpen(true); };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setError('');
    setSaving(true);
    try {
      await api.post('/fixed-assets', {
        ...form,
        depreciation_rate: form.depreciation_rate === '' ? null : form.depreciation_rate,
        vendor_id: form.vendor_id === '' ? null : form.vendor_id,
      });
      setOpen(false);
      await load();
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Could not save this fixed asset');
    } finally {
      setSaving(false);
    }
  };

  const { pageRows, props: pageProps } = usePagination(filtered);

  return <>
    <PageHeader title="Fixed Assets" subtitle="Asset register with depreciation tracking" action={<Button onClick={showAdd}><Boxes size={15} /> Add Asset</Button>}  toolbar={<><div className="search-box"><Search size={16} /><input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search asset code, name or category..." /></div></>}/>
        <Card className="list-card">{loading ? <Loading /> : <div className="table-wrap"><table className="data-table"><thead><tr><th>Asset Code</th><th>Asset Name</th><th>Category</th><th>Purchase Date</th><th>Cost</th><th>Accum. Depreciation</th><th>Book Value</th><th>Status</th><th>Action</th></tr></thead><tbody>{pageRows.map(asset => <tr key={asset.id}>
      <td className="nowrap">{asset.code}</td><td title={asset.name}><b>{asset.name}</b></td>
      <td>{asset.category}</td>
      <td>{shortDate(asset.purchase_date)}</td>
      <td className="amount">{currency(asset.purchase_cost, 2)}</td>
      <td className="amount">{currency(asset.accumulated_depreciation, 2)}</td>
      <td className="amount"><b>{currency(Number(asset.purchase_cost) - Number(asset.accumulated_depreciation), 2)}</b></td>
      <td><Status value={asset.status} /></td>
      <td><button className="mini-button" title="View" onClick={() => navigate(`/fixed-assets/${asset.id}`)}><Eye size={14} /></button></td>
    </tr>)}
    {!filtered.length && <tr><td colSpan={9} className="muted">No fixed assets recorded</td></tr>}
    </tbody></table></div>}<Pagination {...pageProps} noun="fixed assets" /></Card>

    <Modal open={open} onClose={() => setOpen(false)} title="Add Fixed Asset" width={720}>
      <form onSubmit={submit}>
        <div className="form-grid">
          <Field label="Asset Name" required><Input required value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} /></Field>
          <Field label="Category"><Select value={form.category} onChange={e => setForm({ ...form, category: e.target.value })}>{categories.map(c => <option key={c}>{c}</option>)}</Select></Field>
          <Field label="Purchase Date" required><Input type="date" required value={form.purchase_date} onChange={e => setForm({ ...form, purchase_date: e.target.value })} /></Field>
          <Field label="Purchase Cost" required><Input type="number" step="0.01" min="0.01" required value={form.purchase_cost} onChange={e => setForm({ ...form, purchase_cost: Number(e.target.value) })} /></Field>
          <Field label="Salvage Value"><Input type="number" step="0.01" min="0" value={form.salvage_value} onChange={e => setForm({ ...form, salvage_value: Number(e.target.value) })} /></Field>
          <Field label="Useful Life (Years)" required><Input type="number" step="0.5" min="0.5" required value={form.useful_life_years} onChange={e => setForm({ ...form, useful_life_years: Number(e.target.value) })} /></Field>
          <Field label="Depreciation Method"><Select value={form.depreciation_method} onChange={e => setForm({ ...form, depreciation_method: e.target.value })}><option>Straight Line</option><option>Written Down Value</option></Select></Field>
          {form.depreciation_method === 'Written Down Value' && <Field label="Depreciation Rate (% p.a.)" required><Input type="number" step="0.01" min="0.01" required value={form.depreciation_rate} onChange={e => setForm({ ...form, depreciation_rate: e.target.value === '' ? '' : Number(e.target.value) })} /></Field>}
          <Field label="Vendor (optional)"><Select value={form.vendor_id} onChange={e => setForm({ ...form, vendor_id: e.target.value ? Number(e.target.value) : '' })}><option value="">None</option>{vendors.map(v => <option key={v.id} value={v.id}>{v.name}</option>)}</Select></Field>
          <Field label="Payment Mode"><Select value={form.payment_mode} onChange={e => setForm({ ...form, payment_mode: e.target.value })}><option>Bank</option><option>Cash</option></Select></Field>
          <Field label="Location"><Input value={form.location} onChange={e => setForm({ ...form, location: e.target.value })} /></Field>
          <Field label="Notes"><textarea className="input" value={form.notes} onChange={e => setForm({ ...form, notes: e.target.value })} /></Field>
        </div>
        {error && <div className="toast">{error}</div>}
        <div className="form-actions"><Button type="button" tone="secondary" onClick={() => setOpen(false)}>Cancel</Button><Button type="submit" disabled={saving}>Save Asset</Button></div>
      </form>
    </Modal>
  </>;
}