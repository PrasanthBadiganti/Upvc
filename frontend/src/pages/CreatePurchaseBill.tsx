import { useEffect, useMemo, useState } from 'react';
import { Eye, Plus, Save, Trash2, Download } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import api from '../api';
import { Button, Card, Field, Input, Modal, PageHeader, Select } from '../components/UI';
import { PurchaseBillItem, StockItem, Vendor } from '../types';
import { currency } from '../utils';
import { useToastContext } from '../contexts/ToastContext';
import { useKeyboardShortcut, SHORTCUTS } from '../hooks/useKeyboardShortcut';

const emptyItem = (): PurchaseBillItem => ({ description: '', category: '', hsn_code: '', unit: 'Nos', quantity: 1, rate: 0, gst_percent: 18, amount: 0, stock_item_id: null });

export default function CreatePurchaseBill() {
  const navigate = useNavigate();
  const toast = useToastContext();
  const [vendors, setVendors] = useState<Vendor[]>([]);
  const [stockItems, setStockItems] = useState<StockItem[]>([]);
  const [vendorId, setVendorId] = useState<number>(0);
  const [vendorBillNumber, setVendorBillNumber] = useState('');
  const [billDate, setBillDate] = useState(new Date().toISOString().slice(0, 10));
  const [dueDate, setDueDate] = useState(new Date(Date.now() + 30 * 86400000).toISOString().slice(0, 10));
  const [notes, setNotes] = useState('');
  const [items, setItems] = useState<PurchaseBillItem[]>([emptyItem()]);
  const [saving, setSaving] = useState(false);
  const [detailModalOpen, setDetailModalOpen] = useState(false);
  const [detailModalIndex, setDetailModalIndex] = useState<number | null>(null);

  useKeyboardShortcut([
    { ...SHORTCUTS.SAVE, onPress: () => save(), disabled: saving },
  ]);

  useEffect(() => {
    api.get('/vendors', { params: { status: 'Active' } }).then(r => { setVendors(r.data); if (r.data[0]) setVendorId(r.data[0].id); });
    api.get('/stock-items').then(r => setStockItems(r.data));
  }, []);

  const update = (index: number, key: keyof PurchaseBillItem, value: string) => {
    setItems(prev => prev.map((row, i) => {
      if (i !== index) return row;
      const numericFields = ['quantity', 'rate', 'gst_percent'];
      const next = { ...row, [key]: numericFields.includes(String(key)) ? Number(value) : value } as PurchaseBillItem;
      if (numericFields.includes(String(key))) next.amount = Number((Number(next.quantity) * Number(next.rate)).toFixed(2));
      return next;
    }));
  };

  const updateStockItem = (index: number, value: string) => {
    setItems(prev => prev.map((row, i) => i === index ? { ...row, stock_item_id: value ? Number(value) : null } : row));
  };

  const totals = useMemo(() => {
    const subtotal = items.reduce((s, i) => s + Number(i.amount || 0), 0);
    const gst = items.reduce((s, i) => s + Number(i.amount || 0) * Number(i.gst_percent || 0) / 100, 0);
    return { subtotal, gst, grand: subtotal + gst };
  }, [items]);

  const save = async () => {
    if (!vendorId) {
      toast.warning('Please select a vendor');
      return;
    }
    setSaving(true);
    try {
      const payload = { vendor_bill_number: vendorBillNumber, bill_date: billDate, due_date: dueDate, notes, items };
      const { data } = await api.post(`/vendors/${vendorId}/purchase-bills`, payload);
      const vendor = vendors.find(v => v.id === vendorId);
      toast.success(`Purchase bill saved for ${vendor?.name}!`);
      navigate(`/purchase-bills/${data.id}`);
    } catch (err) {
      toast.error('Failed to save purchase bill');
    } finally { setSaving(false); }
  };

  return <>
    <PageHeader title="New Purchase Bill" subtitle="Purchase Bills / New" />
    <Card className="quote-form-card">
      <h3>Vendor & Bill Details</h3>
      <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:15}}>
        <div>
          <Field label="Vendor" required><Select value={vendorId} onChange={e => setVendorId(Number(e.target.value))}><option value={0} disabled>Select vendor...</option>{vendors.map(v => <option key={v.id} value={v.id}>{v.name}</option>)}</Select></Field>
          <Field label="Bill Date" required><Input type="date" value={billDate} onChange={e => setBillDate(e.target.value)} /></Field>
        </div>
        <div>
          <Field label="Vendor Bill No."><Input value={vendorBillNumber} onChange={e => setVendorBillNumber(e.target.value)} /></Field>
          <Field label="Due Date" required><Input type="date" value={dueDate} onChange={e => setDueDate(e.target.value)} /></Field>
        </div>
      </div>
      <div style={{marginTop:15}}>
        <Field label="Notes"><Input value={notes} onChange={e => setNotes(e.target.value)} placeholder="Special instructions or notes..." /></Field>
      </div>
    </Card>

    <Card className="quote-items-card">
      <div style={{display:'flex',alignItems:'center',justifyContent:'space-between',marginBottom:15}}>
        <h3>Bill Items</h3>
        <Button onClick={() => setItems([...items, emptyItem()])} tone="secondary" style={{display:'flex',alignItems:'center',gap:6}}><Plus size={15}/> Add Item</Button>
      </div>
      <div className="table-wrap"><table className="data-table editable-table"><thead><tr><th style={{width:'40px'}}>#</th><th>Description</th><th style={{width:'80px'}}>Qty</th><th style={{width:'100px'}}>Rate (Rs.)</th><th style={{width:'80px'}}>GST %</th><th style={{textAlign:'right',width:'120px'}}>Amount</th><th style={{width:'80px',textAlign:'center'}}>Actions</th></tr></thead><tbody>{items.map((row, i) => <tr key={i}>
        <td style={{textAlign:'center'}}>{i+1}</td>
        <td>
          <input value={row.description} onChange={e => update(i, 'description', e.target.value)} placeholder="Item description" style={{width:'100%'}}/>
          {row.category && <div style={{fontSize:'12px',color:'#60708a',marginTop:2}}>Category: {row.category}</div>}
        </td>
        <td><input type="number" value={row.quantity} onChange={e => update(i, 'quantity', e.target.value)} style={{width:'100%'}}/></td>
        <td><input type="number" value={row.rate} onChange={e => update(i, 'rate', e.target.value)} style={{width:'100%'}}/></td>
        <td><input type="number" value={row.gst_percent} onChange={e => update(i, 'gst_percent', e.target.value)} style={{width:'100%'}}/></td>
        <td className="amount" style={{textAlign:'right',fontWeight:600}}>{currency(row.amount, 2)}</td>
        <td style={{textAlign:'center',display:'flex',gap:4,justifyContent:'center'}}>
          <button type="button" className="icon-btn ghost" title="View details" onClick={()=>{setDetailModalIndex(i);setDetailModalOpen(true);}} style={{padding:'4px 8px'}}><Eye size={14}/></button>
          <button type="button" className="icon-btn ghost" title="Delete" onClick={() => setItems(items.filter((_, x) => x !== i))} style={{padding:'4px 8px',color:'#ef4444'}}><Trash2 size={14}/></button>
        </td>
      </tr>)}</tbody></table></div>
      <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',padding:'10px 12px',borderTop:'1px solid #e2e8f0',marginTop:10,fontSize:'13px'}}>
        <div><b>Subtotal: {currency(totals.subtotal, 2)}</b></div>
      </div>
    </Card>

    <div style={{display:'grid',gridTemplateColumns:'1fr 300px',gap:12}}>
      <Card className="quote-notes"><small>Additional Notes (Optional)</small><textarea className="input" placeholder="Any special instructions..." value={notes} onChange={e => setNotes(e.target.value)}/></Card>
      <Card className="quote-summary">
        <h3>Bill Summary</h3>
        <div className="summary-line"><span>Subtotal</span><b>{currency(totals.subtotal, 2)}</b></div>
        <div className="summary-line"><span>GST</span><b>{currency(totals.gst, 2)}</b></div>
        <hr style={{border:'none',borderTop:'1px solid #e2e8f0',margin:'10px 0'}}/>
        <div className="summary-line total"><span>Grand Total</span><b style={{fontSize:'16px',color:'#2468f2'}}>{currency(totals.grand, 2)}</b></div>
      </Card>
    </div>

    <div className="quote-actionbar" style={{display:'flex',gap:8}}>
      <Button onClick={save} disabled={saving || !vendorId}><Save size={15}/> Save Bill</Button>
      <Button tone="secondary" onClick={() => window.print()}><Download size={15}/> Print</Button>
    </div>

    <Modal open={detailModalOpen && detailModalIndex !== null} onClose={() => setDetailModalOpen(false)} title={`Item ${(detailModalIndex ?? 0) + 1} - Details`} width={560}>
      {detailModalIndex !== null && <div className="form-grid" style={{gap:15}}>
        <div>
          <small style={{color:'#60708a',fontSize:'11px',textTransform:'uppercase',fontWeight:600}}>Category</small>
          <input className="input" value={items[detailModalIndex].category} onChange={e => update(detailModalIndex, 'category', e.target.value)} placeholder="Category"/>
        </div>
        <div>
          <small style={{color:'#60708a',fontSize:'11px',textTransform:'uppercase',fontWeight:600}}>HSN Code</small>
          <input className="input" value={items[detailModalIndex].hsn_code} onChange={e => update(detailModalIndex, 'hsn_code', e.target.value)} placeholder="HSN Code"/>
        </div>
        <div>
          <small style={{color:'#60708a',fontSize:'11px',textTransform:'uppercase',fontWeight:600}}>Unit</small>
          <input className="input" value={items[detailModalIndex].unit} onChange={e => update(detailModalIndex, 'unit', e.target.value)} placeholder="Unit (Nos/Kg/etc)"/>
        </div>
        <div>
          <small style={{color:'#60708a',fontSize:'11px',textTransform:'uppercase',fontWeight:600}}>Link to Stock Item</small>
          <Select value={items[detailModalIndex].stock_item_id ?? ''} onChange={e => updateStockItem(detailModalIndex, e.target.value)}>
            <option value="">-- Not Linked --</option>
            {stockItems.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
          </Select>
        </div>
      </div>}
      <div className="form-actions" style={{marginTop:20}}>
        <Button tone="secondary" onClick={() => setDetailModalOpen(false)}>Done</Button>
      </div>
    </Modal>
  </>;
}
