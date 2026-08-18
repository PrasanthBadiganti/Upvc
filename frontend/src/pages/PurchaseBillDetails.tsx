import { FormEvent, useEffect, useState } from 'react';
import { Ban, Building2, CalendarDays, Download, FileText, Printer, RotateCcw, WalletCards } from 'lucide-react';
import { useParams } from 'react-router-dom';
import api from '../api';
import { Button, Card, Field, Input, Loading, Modal, PageHeader, Select } from '../components/UI';
import Status from '../components/Status';
import { BankAccount, PurchaseBill } from '../types';
import { currency, shortDate } from '../utils';
import { useConfirm } from '../contexts/ConfirmContext';

export default function PurchaseBillDetails(){
  const confirm = useConfirm();
  const {id}=useParams(); const [bill,setBill]=useState<PurchaseBill|null>(null); const [open,setOpen]=useState(false); const [saving,setSaving]=useState(false);
  const [payment,setPayment]=useState<{payment_date:string;mode:string;reference_number:string;amount:number;paid_by:string;notes:string;bank_account_id:number|null}>({payment_date:new Date().toISOString().slice(0,10),mode:'NEFT',reference_number:'',amount:0,paid_by:'Arun Verma',notes:'',bank_account_id:null});
  const [bankAccounts,setBankAccounts]=useState<BankAccount[]>([]);
  const load=()=>api.get(`/purchase-bills/${id}`).then(r=>{setBill(r.data);setPayment(p=>({...p,amount:Number(r.data.pending_balance)}));}); useEffect(()=>{load();},[id]);
  useEffect(()=>{api.get('/bank-accounts',{params:{status:'Active'}}).then(r=>setBankAccounts(r.data));},[]);
  if(!bill)return <Loading/>;
  const submit=async(e:FormEvent)=>{e.preventDefault();setSaving(true);try{const {data}=await api.post(`/purchase-bills/${bill.id}/payments`,payment);setBill(data);setOpen(false);}finally{setSaving(false)}};
  const download=()=>{const a=document.createElement('a');a.href=`/api/purchase-bills/${bill.id}/pdf`;a.download=`${bill.number}.pdf`;a.click();};
  const cancelled=bill.status==='Cancelled';
  const cancel=async()=>{const paid=bill.status==='Paid';if(!(await confirm({title:`Cancel ${bill.number}?`,message:paid?'This purchase bill is fully paid. Cancelling it will reverse the posting.':'A reversing entry will be posted to the ledger.',confirmLabel:paid?'Cancel anyway':'Cancel bill',cancelLabel:'Keep it',isDangerous:true})))return;const {data}=await api.post(`/purchase-bills/${bill.id}/cancel`,null,{params:{force:paid}});setBill(data);};
  const reopen=async()=>{const {data}=await api.post(`/purchase-bills/${bill.id}/reopen`);setBill(data);};
  return <>
    <PageHeader title="Purchase Bill Details" action={<div className="action-group">{cancelled?<Button tone="secondary" onClick={reopen}><RotateCcw size={15}/> Reopen Bill</Button>:<Button tone="danger" onClick={cancel}><Ban size={15}/> Cancel Bill</Button>}</div>} />
    {cancelled&&<div className="toast">This purchase bill is cancelled. Payments are blocked until it is reopened.</div>}
    <div className="metric-grid invoice-summary-cards">
      <Card className="invoice-summary-card"><div className="metric-icon blue"><FileText size={18}/></div><div><small>Purchase Bill No.</small><strong>{bill.number}</strong></div></Card>
      <Card className="invoice-summary-card"><div className="metric-icon blue"><CalendarDays size={18}/></div><div><small>Bill Date</small><strong>{shortDate(bill.bill_date)}</strong></div></Card>
      <Card className="invoice-summary-card"><div className="metric-icon blue"><Building2 size={18}/></div><div><small>Vendor</small><strong>{bill.vendor.name}</strong><em style={{color:'#60708a'}}>GSTIN: {bill.vendor.gst_number || '--'}</em></div></Card>
      <Card className="invoice-summary-card"><div className="metric-icon blue"><FileText size={18}/></div><div><small>Vendor Bill No.</small><strong>{bill.vendor_bill_number || '--'}</strong></div></Card>
      <Card className="invoice-summary-card"><div className="metric-icon red"><CalendarDays size={18}/></div><div><small>Due Date</small><strong>{shortDate(bill.due_date)}</strong></div></Card>
      <Card className="invoice-summary-card"><div className="metric-icon green"><WalletCards size={18}/></div><div><small>Status</small><strong><Status value={bill.status}/></strong></div></Card>
    </div>
    <div className="invoice-layout">
      <div className="invoice-left">
        <Card className="invoice-table-card"><div className="card-head"><h3>Bill Items</h3></div><div className="table-wrap"><table className="data-table"><thead><tr><th>#</th><th>Description</th><th>HSN</th><th>Category</th><th>Unit</th><th>Qty</th><th>Rate (Rs.)</th><th>GST %</th><th>Amount (Rs.)</th></tr></thead><tbody>{bill.items.map((item,i)=><tr key={item.id}><td>{i+1}</td><td>{item.description}</td><td>{item.hsn_code || '--'}</td><td>{item.category}</td><td>{item.unit}</td><td>{item.quantity}</td><td className="amount">{Number(item.rate).toLocaleString('en-IN',{minimumFractionDigits:2})}</td><td>{item.gst_percent}%</td><td className="amount">{Number(item.amount).toLocaleString('en-IN',{minimumFractionDigits:2})}</td></tr>)}<tr className="invoice-totals"><td colSpan={7}/><td>Subtotal</td><td className="amount">{currency(bill.subtotal,2)}</td></tr>{Number(bill.igst)>0?<tr className="invoice-totals"><td colSpan={7}/><td>IGST</td><td className="amount">{currency(bill.igst,2)}</td></tr>:<><tr className="invoice-totals"><td colSpan={7}/><td>CGST (9%)</td><td className="amount">{currency(bill.cgst,2)}</td></tr><tr className="invoice-totals"><td colSpan={7}/><td>SGST (9%)</td><td className="amount">{currency(bill.sgst,2)}</td></tr></>}<tr className="invoice-totals grand"><td colSpan={7}/><td>Grand Total</td><td className="amount">{currency(bill.grand_total,2)}</td></tr></tbody></table></div></Card>
        <Card className="invoice-table-card"><div className="card-head"><h3>Payment History</h3></div><div className="table-wrap"><table className="data-table"><thead><tr><th>#</th><th>Payment Date</th><th>Mode</th><th>Bank Account</th><th>Reference No.</th><th>Amount (Rs.)</th><th>Paid By</th><th>Notes</th></tr></thead><tbody>{bill.payments.length?bill.payments.map((p,i)=><tr key={p.id}><td>{i+1}</td><td>{shortDate(p.payment_date)}</td><td>{p.mode}</td><td>{p.bank_account?.name || '--'}</td><td>{p.reference_number}</td><td className="amount">{currency(p.amount,2)}</td><td>{p.paid_by}</td><td>{p.notes}</td></tr>):<tr><td colSpan={8} className="muted">No payments recorded</td></tr>}</tbody></table></div></Card>
        <div className="invoice-actions"><Button onClick={()=>setOpen(true)} disabled={cancelled||Number(bill.pending_balance)<=0}>+ Record Payment</Button><Button tone="secondary" onClick={()=>window.print()}><Printer size={15}/> Print</Button><Button tone="secondary" onClick={download}><Download size={15}/> Download PDF</Button></div>
      </div>
      <aside>
        <Card className="payment-summary"><h3>Payment Summary</h3><div className="payment-number"><span>Grand Total</span><strong style={{color:'#1561ec'}}>{currency(bill.grand_total,2)}</strong></div><div className="payment-number green"><span>Paid Amount</span><strong>{currency(bill.paid_amount,2)}</strong></div><div className="payment-number red"><span>Pending Balance</span><strong>{currency(bill.pending_balance,2)}</strong></div></Card>
      </aside>
    </div>
    <Modal open={open} onClose={()=>setOpen(false)} title={`Record Payment - ${bill.number}`} width={560}><form onSubmit={submit}><div className="form-grid"><Field label="Payment Date" required><Input type="date" required value={payment.payment_date} onChange={e=>setPayment({...payment,payment_date:e.target.value})}/></Field><Field label="Mode"><Select value={payment.mode} onChange={e=>setPayment({...payment,mode:e.target.value})}><option>NEFT</option><option>UPI</option><option>Cash</option><option>Cheque</option><option>Card</option></Select></Field><Field label="Bank Account"><Select value={payment.bank_account_id ?? ''} onChange={e=>setPayment({...payment,bank_account_id:e.target.value?Number(e.target.value):null})}><option value="">-- None --</option>{bankAccounts.map(a=><option key={a.id} value={a.id}>{a.name}</option>)}</Select></Field><Field label="Reference Number"><Input value={payment.reference_number} onChange={e=>setPayment({...payment,reference_number:e.target.value})}/></Field><Field label="Amount" required><Input type="number" min="1" max={Number(bill.pending_balance)} step="0.01" value={payment.amount} onChange={e=>setPayment({...payment,amount:Number(e.target.value)})}/></Field><Field label="Paid By"><Input value={payment.paid_by} onChange={e=>setPayment({...payment,paid_by:e.target.value})}/></Field><Field label="Notes"><Input value={payment.notes} onChange={e=>setPayment({...payment,notes:e.target.value})}/></Field></div><div className="form-actions"><Button type="button" tone="secondary" onClick={()=>setOpen(false)}>Cancel</Button><Button type="submit" disabled={saving}>Record Payment</Button></div></form></Modal>
  </>;
}
