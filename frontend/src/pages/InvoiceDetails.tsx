import { FormEvent, useEffect, useMemo, useState } from 'react';
import { Ban, CalendarDays, Check, Download, FileMinus, FilePlus2, FileText, MapPin, Printer, RotateCcw, Share2, UserRound, WalletCards } from 'lucide-react';
import { useNavigate, useParams } from 'react-router-dom';
import api from '../api';
import { Button, Card, Field, Input, Loading, Modal, PageHeader, Select } from '../components/UI';
import Status from '../components/Status';
import { Invoice, NoteItem } from '../types';
import { currency, shortDate } from '../utils';

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
  const navigate=useNavigate();
  const {id}=useParams(); const [invoice,setInvoice]=useState<Invoice|null>(null); const [open,setOpen]=useState(false); const [saving,setSaving]=useState(false);
  const [payment,setPayment]=useState({payment_date:new Date().toISOString().slice(0,10),mode:'NEFT',reference_number:'',amount:0,received_by:'Arun Verma',notes:''});
  const [noteType,setNoteType]=useState<'credit'|'debit'|null>(null);
  const [noteForm,setNoteForm]=useState<{note_date:string;reason:string;items:NoteItem[]}>({note_date:new Date().toISOString().slice(0,10),reason:'',items:[]});
  const [noteSaving,setNoteSaving]=useState(false);
  const load=()=>api.get(`/invoices/${id}`).then(r=>{setInvoice(r.data);setPayment(p=>({...p,amount:Number(r.data.pending_balance)}));}); useEffect(()=>{load();},[id]);
  const noteTotals=useMemo(()=>{
    const subtotal=noteForm.items.reduce((s,i)=>s+Number(i.amount||0),0);
    const gst=noteForm.items.reduce((s,i)=>s+Number(i.amount||0)*Number(i.gst_percent||0)/100,0);
    return {subtotal,gst,grand:subtotal+gst};
  },[noteForm.items]);
  if(!invoice)return <Loading/>;
  const submit=async(e:FormEvent)=>{e.preventDefault();setSaving(true);try{const {data}=await api.post(`/invoices/${invoice.id}/payments`,payment);setInvoice(data);setOpen(false);}finally{setSaving(false)}};
  const download=()=>{const a=document.createElement('a');a.href=`/api/invoices/${invoice.id}/pdf`;a.download=`${invoice.number}.pdf`;a.click();};
  const receipt=(paymentId:number)=>{const a=document.createElement('a');a.href=`/api/payments/${paymentId}/receipt`;a.download=`Receipt-${invoice.number}-${paymentId}.pdf`;a.click();};
  const share=async()=>{await navigator.clipboard.writeText(`${window.location.origin}/invoices/${invoice.id}`);alert('Invoice link copied');};
  const cancelled=invoice.status==='Cancelled';
  const cancel=async()=>{const paid=invoice.status==='Paid';if(!window.confirm(paid?'This invoice is fully paid. Cancel it anyway?':'Cancel this invoice?'))return;const {data}=await api.post(`/invoices/${invoice.id}/cancel`,null,{params:{force:paid}});setInvoice(data);};
  const reopen=async()=>{const {data}=await api.post(`/invoices/${invoice.id}/reopen`);setInvoice(data);};
  const advance=Number(invoice.grand_total)*.5, forty=Number(invoice.grand_total)*.4, ten=Number(invoice.grand_total)*.1;

  const openNote=(type:'credit'|'debit')=>{setNoteType(type);setNoteForm({note_date:new Date().toISOString().slice(0,10),reason:'',items:invoice.items.map(noteItemFromInvoiceItem)});};
  const updateNoteItem=(index:number,key:keyof NoteItem,value:string)=>{
    setNoteForm(prev=>({...prev,items:prev.items.map((row,i)=>{
      if(i!==index) return row;
      const next={...row,[key]:value} as NoteItem;
      if(key==='quantity'||key==='rate') next.amount=Number((Number(next.quantity)*Number(next.rate)).toFixed(2));
      return next;
    })}));
  };
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
    <PageHeader title="Invoice Details" action={<div className="action-group">{cancelled?<Button tone="secondary" onClick={reopen}><RotateCcw size={15}/> Reopen Invoice</Button>:<Button tone="danger" onClick={cancel}><Ban size={15}/> Cancel Invoice</Button>}</div>} />
    {cancelled&&<div className="toast">This invoice is cancelled. Payments are blocked until it is reopened.</div>}
    {invoice.quotation && <div className="invoice-badge"><span className="badge green"><Check size={13}/> Converted from Quotation {invoice.quotation.number}</span></div>}
    <div className="metric-grid invoice-summary-cards">
      <Card className="invoice-summary-card"><div className="metric-icon blue"><FileText size={18}/></div><div><small>Invoice Number</small><strong>{invoice.number}</strong></div></Card>
      <Card className="invoice-summary-card"><div className="metric-icon blue"><CalendarDays size={18}/></div><div><small>Invoice Date</small><strong>{shortDate(invoice.invoice_date)}</strong></div></Card>
      <Card className="invoice-summary-card"><div className="metric-icon blue"><UserRound size={18}/></div><div><small>Customer</small><strong>{invoice.customer.name}</strong><em style={{color:'#60708a'}}>GSTIN: {invoice.customer.gst_number || '--'}</em></div></Card>
      <Card className="invoice-summary-card"><div className="metric-icon blue"><MapPin size={18}/></div><div><small>Project Site</small><strong>{invoice.customer.project_site}</strong></div></Card>
      <Card className="invoice-summary-card"><div className="metric-icon red"><CalendarDays size={18}/></div><div><small>Due Date</small><strong>{shortDate(invoice.due_date)}</strong><em>30 days remaining</em></div></Card>
      <Card className="invoice-summary-card"><div className="metric-icon green"><WalletCards size={18}/></div><div><small>Status</small><strong><Status value={invoice.status}/></strong></div></Card>
    </div>
    <div className="invoice-layout">
      <div className="invoice-left">
        <Card className="invoice-table-card"><div className="card-head"><h3>Invoice Items Summary</h3></div><div className="table-wrap"><table className="data-table"><thead><tr><th>#</th><th>Item Description</th><th>HSN</th><th>Category</th><th>Unit</th><th>Qty</th><th>Rate (Rs.)</th><th>GST %</th><th>Amount (Rs.)</th></tr></thead><tbody>{invoice.items.map((item,i)=><tr key={item.id}><td>{i+1}</td><td>{item.description}</td><td>{item.hsn_code || '--'}</td><td>{item.category}</td><td>{item.unit}</td><td>{item.quantity}</td><td className="amount">{Number(item.rate).toLocaleString('en-IN',{minimumFractionDigits:2})}</td><td>{item.gst_percent}%</td><td className="amount">{Number(item.amount).toLocaleString('en-IN',{minimumFractionDigits:2})}</td></tr>)}<tr className="invoice-totals"><td colSpan={7}/><td>Subtotal</td><td className="amount">{currency(invoice.subtotal,2)}</td></tr>{Number(invoice.igst)>0?<tr className="invoice-totals"><td colSpan={7}/><td>IGST</td><td className="amount">{currency(invoice.igst,2)}</td></tr>:<><tr className="invoice-totals"><td colSpan={7}/><td>CGST (9%)</td><td className="amount">{currency(invoice.cgst,2)}</td></tr><tr className="invoice-totals"><td colSpan={7}/><td>SGST (9%)</td><td className="amount">{currency(invoice.sgst,2)}</td></tr></>}<tr className="invoice-totals grand"><td colSpan={7}/><td>Grand Total</td><td className="amount">{currency(invoice.grand_total,2)}</td></tr></tbody></table></div></Card>
        <Card className="invoice-table-card"><div className="card-head"><h3>Payment History</h3></div><div className="table-wrap"><table className="data-table"><thead><tr><th>#</th><th>Payment Date</th><th>Mode of Payment</th><th>Reference No.</th><th>Amount (Rs.)</th><th>Received By</th><th>Notes</th><th>Receipt</th></tr></thead><tbody>{invoice.payments.length?invoice.payments.map((p,i)=><tr key={p.id}><td>{i+1}</td><td>{shortDate(p.payment_date)}</td><td>{p.mode}</td><td>{p.reference_number}</td><td className="amount">{currency(p.amount,2)}</td><td>{p.received_by}</td><td>{p.notes}</td><td><button className="mini-button" title="Download receipt" onClick={()=>receipt(p.id)}><Download size={14}/></button></td></tr>):<tr><td colSpan={8} className="muted">No payments recorded</td></tr>}</tbody></table></div></Card>
        <div className="invoice-actions"><Button onClick={()=>setOpen(true)} disabled={cancelled||Number(invoice.pending_balance)<=0}>+ Record Payment</Button><Button tone="secondary" onClick={()=>openNote('credit')} disabled={cancelled||Number(invoice.pending_balance)<=0}><FileMinus size={15}/> Create Credit Note</Button><Button tone="secondary" onClick={()=>openNote('debit')} disabled={cancelled}><FilePlus2 size={15}/> Create Debit Note</Button><Button tone="secondary" onClick={()=>window.print()}><Printer size={15}/> Print Invoice</Button><Button tone="secondary" onClick={download}><Download size={15}/> Download PDF</Button><Button tone="secondary" onClick={share}><Share2 size={15}/> Share Invoice</Button></div>
      </div>
      <aside>
        <Card className="payment-summary"><h3>Payment Summary</h3><div className="payment-number"><span>Grand Total</span><strong style={{color:'#1561ec'}}>{currency(invoice.grand_total,2)}</strong></div><div className="payment-number green"><span>Paid Amount</span><strong>{currency(invoice.paid_amount,2)}</strong></div><div className="payment-number red"><span>Pending Balance</span><strong>{currency(invoice.pending_balance,2)}</strong></div><hr style={{border:0,borderTop:'1px solid #e2e8f0'}}/><div className="payment-number"><span>Next Due</span><strong>{currency(Math.min(Number(invoice.pending_balance),forty),2)}</strong></div><div className="payment-number"><span>Next Due On</span><b>{shortDate(invoice.due_date)}</b></div></Card>
        <Card className="payment-schedule"><h3>Payment Schedule</h3><div className="schedule-step"><div className="step-dot done"><Check size={13}/></div><div><b>50% Advance</b><small>Due: {shortDate(invoice.invoice_date)}</small></div><div style={{textAlign:'right'}}><b>{currency(advance,2)}</b><span className="badge green">{Number(invoice.paid_amount)>=advance?'Paid':'Partial'}</span></div></div><div className="schedule-step"><div className="step-dot">2</div><div><b>40% Before Delivery</b><small>Due: {shortDate(invoice.due_date)}</small><div className="progress"><span style={{width:`${Math.min(100,Math.max(0,(Number(invoice.paid_amount)-advance)/forty*100))}%`}}/></div></div><div style={{textAlign:'right'}}><b>{currency(forty,2)}</b><span className="badge blue">Pending</span></div></div><div className="schedule-step"><div className="step-dot">3</div><div><b>10% After Installation</b><small>Due: {shortDate(new Date(new Date(invoice.due_date).getTime()+15*86400000).toISOString())}</small><div className="progress"><span style={{width:'0%'}}/></div></div><div style={{textAlign:'right'}}><b>{currency(ten,2)}</b><span className="badge slate">Pending</span></div></div></Card>
      </aside>
    </div>
    <Modal open={open} onClose={()=>setOpen(false)} title={`Record Payment - ${invoice.number}`} width={560}><form onSubmit={submit}><div className="form-grid"><Field label="Payment Date" required><Input type="date" required value={payment.payment_date} onChange={e=>setPayment({...payment,payment_date:e.target.value})}/></Field><Field label="Mode"><Select value={payment.mode} onChange={e=>setPayment({...payment,mode:e.target.value})}><option>NEFT</option><option>UPI</option><option>Cash</option><option>Cheque</option><option>Card</option></Select></Field><Field label="Reference Number"><Input value={payment.reference_number} onChange={e=>setPayment({...payment,reference_number:e.target.value})}/></Field><Field label="Amount" required><Input type="number" min="1" max={Number(invoice.pending_balance)} step="0.01" value={payment.amount} onChange={e=>setPayment({...payment,amount:Number(e.target.value)})}/></Field><Field label="Received By"><Input value={payment.received_by} onChange={e=>setPayment({...payment,received_by:e.target.value})}/></Field><Field label="Notes"><Input value={payment.notes} onChange={e=>setPayment({...payment,notes:e.target.value})}/></Field></div><div className="form-actions"><Button type="button" tone="secondary" onClick={()=>setOpen(false)}>Cancel</Button><Button type="submit" disabled={saving}>Record Payment</Button></div></form></Modal>

    <Modal open={noteType!==null} onClose={()=>setNoteType(null)} title={`Create ${noteType==='credit'?'Credit':'Debit'} Note - ${invoice.number}`} width={860}>
      <form onSubmit={submitNote}>
        <div className="form-grid">
          <Field label="Note Date" required><Input type="date" required value={noteForm.note_date} onChange={e=>setNoteForm({...noteForm,note_date:e.target.value})}/></Field>
          <Field label="Reason" required><Input required value={noteForm.reason} onChange={e=>setNoteForm({...noteForm,reason:e.target.value})} placeholder={noteType==='credit'?'e.g. Damaged panel returned':'e.g. Installation undercharged'}/></Field>
        </div>
        <div className="table-wrap"><table className="data-table editable-table"><thead><tr><th>Description</th><th>HSN</th><th>Qty</th><th>Rate (Rs.)</th><th>GST %</th><th>Amount (Rs.)</th></tr></thead><tbody>{noteForm.items.map((row,i)=><tr key={i}>
          <td><input value={row.description} onChange={e=>updateNoteItem(i,'description',e.target.value)}/></td>
          <td><input value={row.hsn_code} onChange={e=>updateNoteItem(i,'hsn_code',e.target.value)}/></td>
          <td><input type="number" value={row.quantity} onChange={e=>updateNoteItem(i,'quantity',e.target.value)}/></td>
          <td><input type="number" value={row.rate} onChange={e=>updateNoteItem(i,'rate',e.target.value)}/></td>
          <td><input type="number" value={row.gst_percent} onChange={e=>updateNoteItem(i,'gst_percent',e.target.value)}/></td>
          <td className="amount">{currency(row.amount,2)}</td>
        </tr>)}</tbody></table></div>
        <div className="summary-line"><span>Subtotal</span><span>{currency(noteTotals.subtotal,2)}</span></div>
        <div className="summary-line"><span>GST</span><span>{currency(noteTotals.gst,2)}</span></div>
        <div className="summary-line total"><span>{noteType==='credit'?'Credit':'Debit'} Total</span><span>{currency(noteTotals.grand,2)}</span></div>
        <div className="form-actions"><Button type="button" tone="secondary" onClick={()=>setNoteType(null)}>Cancel</Button><Button type="submit" disabled={noteSaving}>{`Issue ${noteType==='credit'?'Credit':'Debit'} Note`}</Button></div>
      </form>
    </Modal>
  </>;
}
