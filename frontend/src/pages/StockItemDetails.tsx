import { FormEvent, useEffect, useState } from 'react';
import { ArrowDownCircle, ArrowUpCircle, Boxes } from 'lucide-react';
import { useParams } from 'react-router-dom';
import api from '../api';
import { Button, Card, Field, Input, Loading, Modal, PageHeader, Select } from '../components/UI';
import { StockItem } from '../types';
import { quantity, shortDate } from '../utils';

export default function StockItemDetails() {
  const { id } = useParams();
  const [item, setItem] = useState<StockItem | null>(null);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ movement_date: new Date().toISOString().slice(0, 10), movement_type: 'In', quantity: 0, reason: 'Manual', reference: '', notes: '' });
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);

  const load = () => api.get(`/stock-items/${id}`).then(r => setItem(r.data));
  useEffect(() => { load(); }, [id]);
  if (!item) return <Loading />;

  const isLow = Number(item.reorder_level) > 0 && Number(item.quantity_on_hand) <= Number(item.reorder_level);

  const showMovement = (type: string) => { setForm({ movement_date: new Date().toISOString().slice(0, 10), movement_type: type, quantity: 0, reason: type === 'In' ? 'Manual' : 'Issued for Project', reference: '', notes: '' }); setError(''); setOpen(true); };

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    setSaving(true);
    try {
      await api.post(`/stock-items/${item.id}/movements`, form);
      setOpen(false);
      await load();
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Could not record this movement');
    } finally {
      setSaving(false);
    }
  };

  return <>
    <PageHeader title="Stock Item Details" action={<div className="action-group"><Button tone="secondary" onClick={() => showMovement('In')}><ArrowDownCircle size={15} /> Stock In</Button><Button tone="secondary" onClick={() => showMovement('Out')}><ArrowUpCircle size={15} /> Stock Out</Button></div>} />
    <div className="metric-grid invoice-summary-cards">
      <Card className="invoice-summary-card"><div className="metric-icon blue"><Boxes size={18} /></div><div><small>Item</small><strong>{item.name}</strong><em style={{ color: '#60708a' }}>{item.code} - {item.category}</em></div></Card>
      <Card className={`invoice-summary-card`}><div className={`metric-icon ${isLow ? 'red' : 'green'}`}><Boxes size={18} /></div><div><small>On Hand</small><strong>{quantity(item.quantity_on_hand)} {item.unit}</strong></div></Card>
      <Card className="invoice-summary-card"><div className="metric-icon blue"><Boxes size={18} /></div><div><small>Reorder Level</small><strong>{quantity(item.reorder_level)} {item.unit}</strong></div></Card>
      <Card className="invoice-summary-card"><div className="metric-icon blue"><Boxes size={18} /></div><div><small>Status</small><strong>{item.status}</strong></div></Card>
    </div>

    <Card className="invoice-table-card">
      <div className="card-head"><h3>Movement History</h3></div>
      <div className="table-wrap"><table className="data-table"><thead><tr><th>Date</th><th>Type</th><th>Reason</th><th>Reference</th><th>Quantity</th><th>Balance After</th></tr></thead><tbody>
        {item.movements.slice().reverse().map(m => <tr key={m.id}>
          <td>{shortDate(m.movement_date)}</td>
          <td>{m.movement_type}</td>
          <td>{m.reason}</td>
          <td>{m.reference || '--'}</td>
          <td className={`amount ${m.movement_type === 'In' ? 'success' : 'danger'}`}>{m.movement_type === 'In' ? '+' : '-'}{quantity(m.quantity)}</td>
          <td className="amount"><b>{quantity(m.balance_after)} {item.unit}</b></td>
        </tr>)}
        {!item.movements.length && <tr><td colSpan={6} className="muted">No stock movements yet</td></tr>}
      </tbody></table></div>
    </Card>

    <Modal open={open} onClose={() => setOpen(false)} title={form.movement_type === 'In' ? 'Record Stock In' : 'Record Stock Out'} width={480}>
      <form onSubmit={submit}>
        <div className="form-grid">
          <Field label="Date" required><Input type="date" required value={form.movement_date} onChange={e => setForm({ ...form, movement_date: e.target.value })} /></Field>
          <Field label="Quantity" required><Input type="number" min="0.01" step="0.01" required value={form.quantity} onChange={e => setForm({ ...form, quantity: Number(e.target.value) })} /></Field>
          <Field label="Reason">
            <Select value={form.reason} onChange={e => setForm({ ...form, reason: e.target.value })}>
              {form.movement_type === 'In' ? <><option>Manual</option><option>Opening Stock</option><option>Return</option></> : <><option>Issued for Project</option><option>Wastage</option><option>Adjustment</option></>}
            </Select>
          </Field>
          <Field label="Reference"><Input value={form.reference} onChange={e => setForm({ ...form, reference: e.target.value })} placeholder="e.g. project or site name" /></Field>
          <Field label="Notes"><Input value={form.notes} onChange={e => setForm({ ...form, notes: e.target.value })} /></Field>
        </div>
        {error && <div className="toast">{error}</div>}
        <div className="form-actions"><Button type="button" tone="secondary" onClick={() => setOpen(false)}>Cancel</Button><Button type="submit" disabled={saving}>Save</Button></div>
      </form>
    </Modal>
  </>;
}
