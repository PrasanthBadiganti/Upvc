import { FormEvent, useEffect, useMemo, useState } from 'react';
import { Ban, CalendarDays, Check, Download, FileMinus, FilePlus2, FileText, MapPin, Plus, Printer, RotateCcw, Share2, Trash2, UserRound, WalletCards } from 'lucide-react';
import { useNavigate, useParams } from 'react-router-dom';
import api from '../api';
import { Button, Card, Field, Input, Loading, Modal, PageHeader, Select } from '../components/UI';
import Status from '../components/Status';
import { BankAccount, BusinessSettings, Invoice, NoteItem } from '../types';
import { InvoicePrintDoc } from '../components/PrintDocument';
import { printDocument } from '../lib/print';
import { currency, shortDate } from '../utils';
import { useConfirm } from '../contexts/ConfirmContext';

// Directly-raised invoices and migrated opening balances carry no window
// dimensions, so those cells read as a dash rather than a misleading zero.
const dim = (value: number | string | undefined) =>
  Number(value || 0) > 0 ? Number(value).toLocaleString('en-IN', { maximumFractionDigits: 0 }) : '--';

// The size is now its own column, so drop it from the name the way the quotation does.
const itemName = (it: Invoice['items'][number]) =>
  [it.category, it.style].filter(Boolean).join(' ').trim() || it.description;

const noteItemFromInvoiceItem = (item: Invoice['items'][number]): NoteItem => ({
  description: item.description,
  category: item.category,
  hsn_code: item.hsn_code || '',
  unit: item.unit,
  quantity: item.quantity,
  rate: item.rate,
  gst_percent: item.gst_percent,
  amount: item.amount,
});

export default function InvoiceDetails(){
  const confirm = useConfirm();
  const navigate=useNavigate();
  const {id}=useParams(); const [invoice,setInvoice]=useState<Invoice|null>(null); const [open,setOpen]=useState(false); const [saving,setSaving]=useState(false);
  const [payment,setPayment]=useState<{payment_date:string;mode:string;reference_number:string;amount:number;received_by:string;notes:string;bank_account_id:number|null}>({payment_date:new Date().toISOString().slice(0,10),mode:'NEFT',reference_number:'',amount:0,received_by:'Arun Verma',notes:'',bank_account_id:null});
  const [bankAccounts,setBankAccounts]=useState<BankAccount[]>([]);
  const [business,setBusiness]=useState<BusinessSettings|null>(null);
  const [noteType,setNoteType]=useState<'credit'|'debit'|null>(null);
  const [noteForm,setNoteForm]=useState<{note_date:string;reason:string;items:NoteItem[]}>({note_date:new Date().toISOString().slice(0,10),reason:'',items:[]});
  const [noteSaving,setNoteSaving]=useState(false);
  const load=()=>api.get(`/invoices/${id}`).then(r=>{setInvoice(r.data);setPayment(p=>({...p,amount:Number(r.data.pending_balance)}));}); useEffect(()=>{load();},[id]);
  useEffect(()=>{api.get('/bank-accounts',{params:{status:'Active'}}).then(r=>setBankAccounts(r.data));},[]);
  useEffect(()=>{api.get('/business-settings').then(r=>setBusiness(r.data));},[]);
  const noteTotals=useMemo(()=>{
    const subtotal=noteForm.items.reduce((s,i)=>s+Number(i.amount||0),0);
    const gst=noteForm.items.reduce((s,i)=>s+Number(i.amount||0)*Number(i.gst_percent||0)/100,0);
    return {subtotal,gst,grand:subtotal+gst};
  },[noteForm.items]);
  if(!invoice)return <Loading/>;
  const submit=async(e:FormEvent)=>{e.preventDefault();setSaving(true);try{const {data}=await api.post(`/invoices/${invoice.id}/payments`,payment);setInvoice(data);setOpen(false);}finally{setSaving(false)}};
  const download=()=>printDocument(`Invoice ${invoice!.number}`);
  const receipt=(paymentId:number)=>{const a=document.createElement('a');a.href=`/api/payments/${paymentId}/receipt`;a.download=`Receipt-${invoice.number}-${paymentId}.pdf`;a.click();};
  const share=async()=>{await navigator.clipboard.writeText(`${window.location.origin}/invoices/${invoice.id}`);alert('Invoice link copied');};
  const cancelled=invoice.status==='Cancelled';
  const cancel=async()=>{const paid=invoice.status==='Paid';if(!(await confirm({title:`Cancel ${invoice.number}?`,message:paid?'This invoice is fully paid. Cancelling it will reverse the posting and clear the receivable.':'A reversing entry will be posted to the ledger.',confirmLabel:paid?'Cancel anyway':'Cancel invoice',cancelLabel:'Keep it',isDangerous:true})))return;const {data}=await api.post(`/invoices/${invoice.id}/cancel`,null,{params:{force:paid}});setInvoice(data);};
  const reopen=async()=>{const {data}=await api.post(`/invoices/${invoice.id}/reopen`);setInvoice(data);};
  const dueDate=new Date(`${invoice.due_date}T00:00:00`);
  const today=new Date(); today.setHours(0,0,0,0);
  const daysToDue=Math.round((dueDate.getTime()-today.getTime())/86400000);
  const dueStatus=Number(invoice.pending_balance)<0?'Credit balance':Number(invoice.pending_balance)===0?'Fully paid':daysToDue<0?`${Math.abs(daysToDue)} day${Math.abs(daysToDue)===1?'':'s'} overdue`:daysToDue===0?'Due today':`${daysToDue} day${daysToDue===1?'':'s'} remaining`;

  const openNote=(type:'credit'|'debit')=>{setNoteType(type);setNoteForm({note_date:new Date().toISOString().slice(0,10),reason:'',items:invoice.items.map(noteItemFromInvoiceItem)});};
  const updateNoteItem=(index:number,key:keyof NoteItem,value:string)=>{
    setNoteForm(prev=>({...prev,items:prev.items.map((row,i)=>{
      if(i!==index) return row;
      const next={...row,[key]:value} as NoteItem;
      if(key==='quantity'||key==='rate') next.amount=Number((Number(next.quantity)*Number(next.rate)).toFixed(2));
      return next;
    })}));
  };
  // A note may cover only part of the invoice: drop the lines that are not being
  // credited/debited rather than zeroing their quantity, so the printed note and
  // the GSTR-1 HSN summary carry only the lines that actually moved.
  const removeNoteItem=(index:number)=>setNoteForm(prev=>({...prev,items:prev.items.filter((_,i)=>i!==index)}));
  const addNoteItem=()=>setNoteForm(prev=>({...prev,items:[...prev.items,{description:'',category:'',hsn_code:'',unit:'Nos',quantity:1,rate:0,gst_percent:invoice?.items[0]?.gst_percent??18,amount:0}]}));
  const submitNote=async(e:FormEvent)=>{
    e.preventDefault();
    if(!noteType) return;
    setNoteSaving(true);
    try{
      const path=noteType==='credit'?'credit-notes':'debit-notes';
      const {data}=await api.post(`/invoices/${invoice.id}/${path}`,{note_date:noteForm.note_date,reason:noteForm.reason,items:noteForm.items});
      navigate(`/${path}/${data.id}`);
    } finally { setNoteSaving(false); }
  };
  return <>
    <PageHeader title="Invoice Details" action={<div className="action-group detail-actions">
      <Button onClick={()=>setOpen(true)} disabled={cancelled||Number(invoice.pending_balance)<=0}><Plus size={15}/> Record Payment</Button>
      <Button tone="secondary" onClick={()=>openNote('credit')} disabled={cancelled}><FileMinus size={15}/> Credit Note</Button>
      <Button tone="secondary" onClick={()=>openNote('debit')} disabled={cancelled}><FilePlus2 size={15}/> Debit Note</Button>
      <Button tone="secondary" onClick={download}><Printer size={15}/> Print / Save PDF</Button>
      <Button tone="secondary" onClick={share}><Share2 size={15}/> Share</Button>
      {cancelled?<Button tone="secondary" onClick={reopen}><RotateCcw size={15}/> Reopen Invoice</Button>:<Button tone="danger" onClick={cancel}><Ban size={15}/> Cancel Invoice</Button>}
    </div>} />
    {cancelled&&<div className="toast">This invoice is cancelled. Payments are blocked until it is reopened.</div>}
    {invoice.quotation && <div className="invoice-badge"><span className="badge green"><Check size={13}/> Converted from Quotation {invoice.quotation.number}</span></div>}
    <div className="metric-grid invoice-summary-cards">
      <Card className="invoice-summary-card"><div className="metric-icon blue"><FileText size={18}/></div><div><small>Invoice Number</small><strong>{invoice.number}</strong></div></Card>
      <Card className="invoice-summary-card"><div className="metric-icon blue"><CalendarDays size={18}/></div><div><small>Invoice Date</small><strong>{shortDate(invoice.invoice_date)}</strong></div></Card>
      <Card className="invoice-summary-card"><div className="metric-icon blue"><UserRound size={18}/></div><div><small>Customer</small><strong>{invoice.customer.name}</strong><em style={{color:'#60708a'}}>GSTIN: {invoice.customer.gst_number || '--'}</em></div></Card>
      <Card className="invoice-summary-card"><div className="metric-icon blue"><MapPin size={18}/></div><div><small>Project Site</small><strong>{invoice.customer.project_site}</strong></div></Card>
      <Card className="invoice-summary-card"><div className="metric-icon red"><CalendarDays size={18}/></div><div><small>Due Date</small><strong>{shortDate(invoice.due_date)}</strong><em>{dueStatus}</em></div></Card>
      <Card className="invoice-summary-card"><div className="metric-icon green"><WalletCards size={18}/></div><div><small>Status</small><strong><Status value={invoice.status}/></strong></div></Card>
    </div>
    <div className="invoice-layout">
      <div className="invoice-left">
        <Card className="invoice-table-card"><div className="card-head"><h3>Invoice Items Summary</h3></div><div className="table-wrap"><table className="data-table"><thead><tr><th>#</th><th>Item</th><th>HSN</th><th>Width (mm)</th><th>Height (mm)</th><th>SFT</th><th>Qty</th><th>Total SFT</th><th>Rate / SFT</th><th>GST %</th><th>Total</th></tr></thead><tbody>{invoice.items.map((item,i)=><tr key={item.id}><td>{i+1}</td><td title={item.description}>{itemName(item)}</td><td>{item.hsn_code || '--'}</td><td className="amount">{dim(item.width_mm)}</td><td className="amount">{dim(item.height_mm)}</td><td className="amount">{dim(Math.round(Number(item.sft||0)))}</td><td className="amount">{dim(item.piece_qty)}</td><td className="amount">{Math.round(Number(item.quantity||0)).toLocaleString('en-IN')}</td><td className="amount">{Number(item.rate).toLocaleString('en-IN',{minimumFractionDigits:2})}</td><td>{item.gst_percent}%</td><td className="amount">{Number(item.amount).toLocaleString('en-IN',{minimumFractionDigits:2})}</td></tr>)}<tr className="invoice-totals"><td colSpan={9}/><td>Subtotal</td><td className="amount">{currency(invoice.subtotal,2)}</td></tr>{Number(invoice.transport)!==0&&<tr className="invoice-totals"><td colSpan={9}/><td>Transport</td><td className="amount">{currency(invoice.transport,2)}</td></tr>}{(invoice.charges??[]).map(ch=><tr className="invoice-totals" key={ch.id}><td colSpan={9}/><td>{ch.label}{!ch.taxable&&<span className="muted"> (no GST)</span>}</td><td className="amount">{currency(ch.amount,2)}</td></tr>)}{Number(invoice.discount)!==0&&<tr className="invoice-totals"><td colSpan={9}/><td>Discount</td><td className="amount">-{currency(invoice.discount,2)}</td></tr>}{Number(invoice.igst)>0?<tr className="invoice-totals"><td colSpan={9}/><td>IGST</td><td className="amount">{currency(invoice.igst,2)}</td></tr>:<><tr className="invoice-totals"><td colSpan={9}/><td>CGST (9%)</td><td className="amount">{currency(invoice.cgst,2)}</td></tr><tr className="invoice-totals"><td colSpan={9}/><td>SGST (9%)</td><td className="amount">{currency(invoice.sgst,2)}</td></tr></>}<tr className="invoice-totals grand"><td colSpan={9}/><td>Grand Total</td><td className="amount">{currency(invoice.grand_total,2)}</td></tr></tbody></table></div></Card>
        <Card className="invoice-table-card"><div className="card-head"><h3>Payment History</h3></div><div className="table-wrap"><table className="data-table"><thead><tr><th>#</th><th>Payment Date</th><th>Mode of Payment</th><th>Bank Account</th><th>Reference No.</th><th>Amount (Rs.)</th><th>Received By</th><th>Notes</th><th>Receipt</th></tr></thead><tbody>{invoice.payments.length?invoice.payments.map((p,i)=><tr key={p.id}><td>{i+1}</td><td>{shortDate(p.payment_date)}</td><td>{p.mode}</td><td>{p.bank_account?.name || '--'}</td><td>{p.reference_number}</td><td className="amount">{currency(p.amount,2)}</td><td>{p.received_by}</td><td>{p.notes}</td><td><button className="mini-button" title="Download receipt" onClick={()=>receipt(p.id)}><Download size={14}/></button></td></tr>):<tr><td colSpan={9} className="muted">No payments recorded</td></tr>}</tbody></table></div></Card>
      </div>
      <aside>
        <Card className="payment-summary"><h3>Payment Summary</h3><div className="payment-number"><span>Grand Total</span><strong style={{color:'#1561ec'}}>{currency(invoice.grand_total,2)}</strong></div><div className="payment-number green"><span>Paid Amount</span><strong>{currency(invoice.paid_amount,2)}</strong></div>{Number(invoice.pending_balance)<0
        ?<div className="payment-number green"><span>Credit Due to Customer</span><strong>{currency(Math.abs(Number(invoice.pending_balance)),2)}</strong></div>
        :<div className="payment-number red"><span>Pending Balance</span><strong>{currency(invoice.pending_balance,2)}</strong></div>}<hr style={{border:0,borderTop:'1px solid #e2e8f0'}}/><div className="payment-number"><span>Payment Due</span><b>{shortDate(invoice.due_date)}</b></div><div className="payment-number"><span>Collection Status</span><strong>{dueStatus}</strong></div></Card>
      </aside>
    </div>
    <Modal open={open} onClose={()=>setOpen(false)} title={`Record Payment - ${invoice.number}`} width={560}><form onSubmit={submit}><div className="form-grid"><Field label="Payment Date" required><Input type="date" required value={payment.payment_date} onChange={e=>setPayment({...payment,payment_date:e.target.value})}/></Field><Field label="Mode"><Select value={payment.mode} onChange={e=>setPayment({...payment,mode:e.target.value})}><option>NEFT</option><option>UPI</option><option>Cash</option><option>Cheque</option><option>Card</option></Select></Field><Field label="Bank Account"><Select value={payment.bank_account_id ?? ''} onChange={e=>setPayment({...payment,bank_account_id:e.target.value?Number(e.target.value):null})}><option value="">-- None --</option>{bankAccounts.map(a=><option key={a.id} value={a.id}>{a.name}</option>)}</Select></Field><Field label="Reference Number"><Input value={payment.reference_number} onChange={e=>setPayment({...payment,reference_number:e.target.value})}/></Field><Field label="Amount" required><Input type="number" min="1" max={Number(invoice.pending_balance)} step="0.01" value={payment.amount} onChange={e=>setPayment({...payment,amount:Number(e.target.value)})}/></Field><Field label="Received By"><Input value={payment.received_by} onChange={e=>setPayment({...payment,received_by:e.target.value})}/></Field><Field label="Notes"><Input value={payment.notes} onChange={e=>setPayment({...payment,notes:e.target.value})}/></Field></div><div className="form-actions"><Button type="button" tone="secondary" onClick={()=>setOpen(false)}>Cancel</Button><Button type="submit" disabled={saving}>Record Payment</Button></div></form></Modal>

    <Modal open={noteType!==null} onClose={()=>setNoteType(null)} title={`Create ${noteType==='credit'?'Credit':'Debit'} Note - ${invoice.number}`} width={860}>
      <form onSubmit={submitNote}>
        <div className="form-grid">
          <Field label="Note Date" required><Input type="date" required value={noteForm.note_date} onChange={e=>setNoteForm({...noteForm,note_date:e.target.value})}/></Field>
          <Field label="Reason" required><Input required value={noteForm.reason} onChange={e=>setNoteForm({...noteForm,reason:e.target.value})} placeholder={noteType==='credit'?'e.g. Damaged panel returned':'e.g. Installation undercharged'}/></Field>
        </div>
        <p className="muted" style={{margin:'0 0 6px',fontSize:12.5}}>{noteType==='credit'?'Remove the lines you are not crediting, or reduce the quantity to credit part of a line.':'Keep only the lines being charged extra, or add a new line for a fresh charge.'}</p>
        <div className="table-wrap"><table className="data-table editable-table"><thead><tr><th>Description</th><th>HSN</th><th>Qty</th><th>Rate (Rs.)</th><th>GST %</th><th>Amount (Rs.)</th><th>Action</th></tr></thead><tbody>{noteForm.items.map((row,i)=><tr key={i}>
          <td><input value={row.description} onChange={e=>updateNoteItem(i,'description',e.target.value)}/></td>
          <td><input value={row.hsn_code} onChange={e=>updateNoteItem(i,'hsn_code',e.target.value)}/></td>
          <td><input type="number" value={row.quantity} onChange={e=>updateNoteItem(i,'quantity',e.target.value)}/></td>
          <td><input type="number" value={row.rate} onChange={e=>updateNoteItem(i,'rate',e.target.value)}/></td>
          <td><input type="number" value={row.gst_percent} onChange={e=>updateNoteItem(i,'gst_percent',e.target.value)}/></td>
          <td className="amount">{currency(row.amount,2)}</td>
          <td><button type="button" className="mini-button" title="Remove this line" onClick={()=>removeNoteItem(i)}><Trash2 size={14}/></button></td>
        </tr>)}
        {!noteForm.items.length && <tr><td colSpan={7} className="muted">No lines. Add at least one line to issue this note.</td></tr>}
        </tbody></table></div>
        <div style={{margin:'8px 0'}}><Button type="button" tone="secondary" onClick={addNoteItem}><Plus size={15}/> Add Line</Button></div>
        <div className="summary-line"><span>Subtotal</span><span>{currency(noteTotals.subtotal,2)}</span></div>
        <div className="summary-line"><span>GST</span><span>{currency(noteTotals.gst,2)}</span></div>
        <div className="summary-line total"><span>{noteType==='credit'?'Credit':'Debit'} Total</span><span>{currency(noteTotals.grand,2)}</span></div>
        <div className="form-actions"><Button type="button" tone="secondary" onClick={()=>setNoteType(null)}>Cancel</Button><Button type="submit" disabled={noteSaving||noteTotals.grand<=0}>{`Issue ${noteType==='credit'?'Credit':'Debit'} Note`}</Button></div>
      </form>
    </Modal>
  {business && <InvoicePrintDoc invoice={invoice} business={business} />}
  </>;
}
