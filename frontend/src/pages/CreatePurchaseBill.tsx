import { useEffect, useMemo, useState } from 'react';
import { Plus, Save, Trash2 } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import api from '../api';
import { Button, Card, Field, Input, PageHeader, Select } from '../components/UI';
import { PurchaseBillItem, Vendor } from '../types';
import { currency } from '../utils';

const emptyItem = (): PurchaseBillItem => ({ description: '', category: '', hsn_code: '', unit: 'Nos', quantity: 1, rate: 0, gst_percent: 18, amount: 0 });

export default function CreatePurchaseBill() {
  const navigate = useNavigate();
  const [vendors, setVendors] = useState<Vendor[]>([]);
  const [vendorId, setVendorId] = useState<number>(0);
  const [vendorBillNumber, setVendorBillNumber] = useState('');
  const [billDate, setBillDate] = useState(new Date().toISOString().slice(0, 10));
  const [dueDate, setDueDate] = useState(new Date(Date.now() + 30 * 86400000).toISOString().slice(0, 10));
  const [notes, setNotes] = useState('');
  const [items, setItems] = useState<PurchaseBillItem[]>([emptyItem()]);
  const [saving, setSaving] = useState(false);

  useEffect(() => { api.get('/vendors', { params: { status: 'Active' } }).then(r => { setVendors(r.data); if (r.data[0]) setVendorId(r.data[0].id); }); }, []);

  const update = (index: number, key: keyof PurchaseBillItem, value: string) => {
    setItems(prev => prev.map((row, i) => {
      if (i !== index) return row;
      const numericFields = ['quantity', 'rate', 'gst_percent'];
      const next = { ...row, [key]: numericFields.includes(String(key)) ? Number(value) : value } as PurchaseBillItem;
      if (numericFields.includes(String(key))) next.amount = Number((Number(next.quantity) * Number(next.rate)).toFixed(2));
      return next;
    }));
  };

  const totals = useMemo(() => {
    const subtotal = items.reduce((s, i) => s + Number(i.amount || 0), 0);
    const gst = items.reduce((s, i) => s + Number(i.amount || 0) * Number(i.gst_percent || 0) / 100, 0);
    return { subtotal, gst, grand: subtotal + gst };
  }, [items]);

  const save = async () => {
    if (!vendorId) return;
    setSaving(true);
    try {
      const payload = { vendor_bill_number: vendorBillNumber, bill_date: billDate, due_date: dueDate, notes, items };
      const { data } = await api.post(`/vendors/${vendorId}/purchase-bills`, payload);
      navigate(`/purchase-bills/${data.id}`);
    } finally { setSaving(false); }
  };

  return <>
    <PageHeader title="New Purchase Bill" subtitle="Purchase Bills / New" />
    <Card className="quote-form-card">
      <h3>Vendor & Bill Details</h3>
      <div className="customer-form-grid">
        <Field label="Vendor" required><Select value={vendorId} onChange={e => setVendorId(Number(e.target.value))}>{vendors.map(v => <option key={v.id} value={v.id}>{v.name}</option>)}</Select></Field>
        <Field label="Vendor Bill No."><Input value={vendorBillNumber} onChange={e => setVendorBillNumber(e.target.value)} /></Field>
        <Field label="Bill Date" required><Input type="date" value={billDate} onChange={e => setBillDate(e.target.value)} /></Field>
        <Field label="Due Date" required><Input type="date" value={dueDate} onChange={e => setDueDate(e.target.value)} /></Field>
        <Field label="Notes"><Input value={notes} onChange={e => setNotes(e.target.value)} /></Field>
      </div>
    </Card>

    <Card className="quote-items-card">
      <div className="quote-items-toolbar"><h3>Bill Items</h3><div className="quote-items-actions"><Button onClick={() => setItems([...items, emptyItem()])}><Plus size={15} /> Add Item</Button></div></div>
      <div className="table-wrap"><table className="data-table editable-table"><thead><tr><th>Description</th><th>Category</th><th>HSN</th><th>Unit</th><th>Qty</th><th>Rate (Rs.)</th><th>GST %</th><th>Amount (Rs.)</th><th>Action</th></tr></thead><tbody>{items.map((row, i) => <tr key={i}>
        <td><input value={row.description} onChange={e => update(i, 'description', e.target.value)} /></td>
        <td><input value={row.category} onChange={e => update(i, 'category', e.target.value)} /></td>
        <td><input value={row.hsn_code} onChange={e => update(i, 'hsn_code', e.target.value)} /></td>
        <td><input value={row.unit} onChange={e => update(i, 'unit', e.target.value)} /></td>
        <td><input type="number" value={row.quantity} onChange={e => update(i, 'quantity', e.target.value)} /></td>
        <td><input type="number" value={row.rate} onChange={e => update(i, 'rate', e.target.value)} /></td>
        <td><input type="number" value={row.gst_percent} onChange={e => update(i, 'gst_percent', e.target.value)} /></td>
        <td className="amount">{currency(row.amount, 2)}</td>
        <td><button className="delete-mini" onClick={() => setItems(items.filter((_, x) => x !== i))}><Trash2 size={14} /></button></td>
      </tr>)}</tbody></table></div>
      <div className="quote-table-footer"><span /><div><b>{currency(totals.subtotal, 2)}</b></div></div>
    </Card>

    <Card className="quote-summary" style={{ maxWidth: 360 }}>
      <h3>Bill Summary</h3>
      <div className="summary-line"><span>Subtotal</span><span>{currency(totals.subtotal, 2)}</span></div>
      <div className="summary-line"><span>GST</span><span>{currency(totals.gst, 2)}</span></div>
      <div className="summary-line total"><span>Grand Total</span><span>{currency(totals.grand, 2)}</span></div>
    </Card>
    <div className="quote-actionbar"><Button onClick={save} disabled={saving || !vendorId}><Save size={15} /> Save Purchase Bill</Button></div>
  </>;
}
