import { Ban, CalendarDays, Download, FileText, Printer, UserRound } from 'lucide-react';
import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import api from '../api';
import { Button, Card, Loading, PageHeader } from '../components/UI';
import Status from '../components/Status';
import { CreditNote } from '../types';
import { currency, shortDate } from '../utils';

export default function CreditNoteDetails(){
  const {id}=useParams(); const [note,setNote]=useState<CreditNote|null>(null);
  const load=()=>api.get(`/credit-notes/${id}`).then(r=>setNote(r.data)); useEffect(()=>{load();},[id]);
  if(!note) return <Loading/>;
  const cancelled=note.status==='Cancelled';
  const download=()=>{const a=document.createElement('a');a.href=`/api/credit-notes/${note.id}/pdf`;a.download=`${note.number}.pdf`;a.click();};
  const cancel=async()=>{if(!window.confirm('Cancel this credit note? The invoice balance will be restored.'))return;const {data}=await api.post(`/credit-notes/${note.id}/cancel`);setNote(data);};
  return <>
    <PageHeader title="Credit Note Details" action={!cancelled?<Button tone="danger" onClick={cancel}><Ban size={15}/> Cancel Credit Note</Button>:undefined} />
    {cancelled&&<div className="toast">This credit note is cancelled. It no longer affects the invoice balance.</div>}
    <div className="metric-grid invoice-summary-cards">
      <Card className="invoice-summary-card"><div className="metric-icon blue"><FileText size={18}/></div><div><small>Credit Note Number</small><strong>{note.number}</strong></div></Card>
      <Card className="invoice-summary-card"><div className="metric-icon blue"><CalendarDays size={18}/></div><div><small>Note Date</small><strong>{shortDate(note.note_date)}</strong></div></Card>
      <Card className="invoice-summary-card"><div className="metric-icon blue"><UserRound size={18}/></div><div><small>Customer</small><strong>{note.customer.name}</strong></div></Card>
      <Card className="invoice-summary-card"><div className="metric-icon blue"><FileText size={18}/></div><div><small>Against Invoice</small><strong><Link to={`/invoices/${note.invoice_id}`}>{note.invoice.number}</Link></strong></div></Card>
      <Card className="invoice-summary-card"><div className="metric-icon green"><FileText size={18}/></div><div><small>Status</small><strong><Status value={note.status}/></strong></div></Card>
    </div>
    <div className="invoice-layout">
      <div className="invoice-left">
        <Card className="invoice-table-card"><div className="card-head"><h3>Credit Note Items</h3></div><div className="table-wrap"><table className="data-table"><thead><tr><th>#</th><th>Description</th><th>HSN</th><th>Category</th><th>Unit</th><th>Qty</th><th>Rate (Rs.)</th><th>GST %</th><th>Amount (Rs.)</th></tr></thead><tbody>{note.items.map((item,i)=><tr key={item.id}><td>{i+1}</td><td>{item.description}</td><td>{item.hsn_code || '--'}</td><td>{item.category}</td><td>{item.unit}</td><td>{item.quantity}</td><td className="amount">{Number(item.rate).toLocaleString('en-IN',{minimumFractionDigits:2})}</td><td>{item.gst_percent}%</td><td className="amount">{Number(item.amount).toLocaleString('en-IN',{minimumFractionDigits:2})}</td></tr>)}<tr className="invoice-totals"><td colSpan={7}/><td>Subtotal</td><td className="amount">{currency(note.subtotal,2)}</td></tr><tr className="invoice-totals"><td colSpan={7}/><td>GST</td><td className="amount">{currency(note.gst,2)}</td></tr><tr className="invoice-totals grand"><td colSpan={7}/><td>Grand Total</td><td className="amount">{currency(note.grand_total,2)}</td></tr></tbody></table></div></Card>
        {note.reason && <Card className="invoice-table-card"><div className="card-head"><h3>Reason</h3></div><p style={{padding:'0 16px 16px'}}>{note.reason}</p></Card>}
        <div className="invoice-actions"><Button tone="secondary" onClick={()=>window.print()}><Printer size={15}/> Print</Button><Button tone="secondary" onClick={download}><Download size={15}/> Download PDF</Button></div>
      </div>
    </div>
  </>;
}
