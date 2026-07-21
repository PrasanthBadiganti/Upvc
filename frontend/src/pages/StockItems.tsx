import { FormEvent, useEffect, useState } from 'react';
import { AlertTriangle, Eye, PackagePlus, Search } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import api from '../api';
import { Button, Card, Field, Input, Loading, Modal, PageHeader, Select } from '../components/UI';
import { StockItem } from '../types';
import { quantity } from '../utils';

const categories = ['Profile', 'Glass', 'Hardware', 'Rubber Gasket', 'Fasteners', 'Other'];

type ItemForm = {
  name: string;
  category: string;
  unit: string;
  hsn_code: string;
  reorder_level: number;
  opening_quantity: number;
  notes: string;
  status: string;
};

const blank: ItemForm = { name: '', category: 'Other', unit: 'Nos', hsn_code: '', reorder_level: 0, opening_quantity: 0, notes: '', status: 'Active' };

export default function StockItems() {
  const navigate = useNavigate();
  const [items, setItems] = useState<StockItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [lowStockOnly, setLowStockOnly] = useState(false);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState<ItemForm>(blank);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);

  const load = () => { setLoading(true); api.get('/stock-items', { params: lowStockOnly ? { low_stock: true } : {} }).then(r => setItems(r.data)).finally(() => setLoading(false)); };
  useEffect(load, [lowStockOnly]);

  const filtered = items.filter(i => `${i.code} ${i.name} ${i.category}`.toLowerCase().includes(search.toLowerCase()));

  const showAdd = () => { setForm(blank); setError(''); setOpen(true); };

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    setSaving(true);
    try {
      await api.post('/stock-items', form);
      setOpen(false);
      await load();
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Could not save this stock item');
    } finally {
      setSaving(false);
    }
  };

  const isLow = (item: StockItem) => Number(item.reorder_level) > 0 && Number(item.quantity_on_hand) <= Number(item.reorder_level);

  return <>
    <PageHeader title="Stock Items" subtitle="Raw material and hardware inventory with reorder tracking" action={<Button onClick={showAdd}><PackagePlus size={15} /> Add Stock Item</Button>} />
    <div className="list-toolbar">
      <div className="search-box"><Search size={16} /><input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search item code, name or category..." /></div>
      <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 14 }}><input type="checkbox" checked={lowStockOnly} onChange={e => setLowStockOnly(e.target.checked)} /> Low stock only</label>
    </div>
    <Card className="list-card">{loading ? <Loading /> : <div className="table-wrap"><table className="data-table"><thead><tr><th>Item</th><th>Category</th><th>Unit</th><th>On Hand</th><th>Reorder Level</th><th>Status</th><th>Action</th></tr></thead><tbody>{filtered.map(item => <tr key={item.id}>
      <td><span className="cell-title">{item.name}</span><span className="cell-sub">{item.code}</span></td>
      <td>{item.category}</td>
      <td>{item.unit}</td>
      <td className={`amount ${isLow(item) ? 'danger' : ''}`}><b>{quantity(item.quantity_on_hand)} {item.unit}</b>{isLow(item) && <AlertTriangle size={13} style={{ marginLeft: 6, verticalAlign: 'middle' }} />}</td>
      <td className="amount">{quantity(item.reorder_level)} {item.unit}</td>
      <td>{item.status}</td>
      <td><button className="mini-button" title="View" onClick={() => navigate(`/stock-items/${item.id}`)}><Eye size={14} /></button></td>
    </tr>)}
    {!filtered.length && <tr><td colSpan={7} className="muted">No stock items found</td></tr>}
    </tbody></table></div>}</Card>

    <Modal open={open} onClose={() => setOpen(false)} title="Add Stock Item" width={640}>
      <form onSubmit={submit}>
        <div className="form-grid">
          <Field label="Item Name" required><Input required value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} /></Field>
          <Field label="Category"><Select value={form.category} onChange={e => setForm({ ...form, category: e.target.value })}>{categories.map(c => <option key={c}>{c}</option>)}</Select></Field>
          <Field label="Unit"><Input value={form.unit} onChange={e => setForm({ ...form, unit: e.target.value })} placeholder="Nos, Mtr, Sq.Ft, Kg..." /></Field>
          <Field label="HSN Code"><Input value={form.hsn_code} onChange={e => setForm({ ...form, hsn_code: e.target.value })} /></Field>
          <Field label="Reorder Level"><Input type="number" min="0" step="0.01" value={form.reorder_level} onChange={e => setForm({ ...form, reorder_level: Number(e.target.value) })} /></Field>
          <Field label="Opening Quantity"><Input type="number" min="0" step="0.01" value={form.opening_quantity} onChange={e => setForm({ ...form, opening_quantity: Number(e.target.value) })} /></Field>
          <Field label="Notes"><textarea className="input" value={form.notes} onChange={e => setForm({ ...form, notes: e.target.value })} /></Field>
        </div>
        {error && <div className="toast">{error}</div>}
        <div className="form-actions"><Button type="button" tone="secondary" onClick={() => setOpen(false)}>Cancel</Button><Button type="submit" disabled={saving}>Save</Button></div>
      </form>
    </Modal>
  </>;
}
