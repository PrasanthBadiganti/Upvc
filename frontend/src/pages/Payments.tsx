import { useEffect, useState } from 'react';
import { Download, IndianRupee } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import api from '../api';
import { Card, Loading, PageHeader } from '../components/UI';
import { Payment } from '../types';
import { currency, shortDate } from '../utils';
import Pagination, { usePagination } from '../components/Pagination';

export default function Payments(){
  const navigate=useNavigate();
  const [rows,setRows]=useState<Payment[]>([]);
  const [loading,setLoading]=useState(true);
  const invoiceNumber=(p:Payment)=>p.invoice?.number || `#${p.invoice_id}`;
  const receipt=(p:Payment)=>{const a=document.createElement('a');a.href=`/api/payments/${p.id}/receipt`;a.download=`Receipt-${invoiceNumber(p)}-${p.id}.pdf`;a.click();};
  useEffect(()=>{api.get('/payments').then(r=>setRows(r.data)).finally(()=>setLoading(false))},[]);
  const { pageRows, props: pageProps } = usePagination(rows);
  return <><PageHeader title="Payments" subtitle="All customer collections and payment references"/><Card className="list-card">{loading?<Loading/>:<div className="table-wrap"><table className="data-table"><thead><tr><th>Receipt No.</th><th>Invoice</th><th>Payment Date</th><th>Mode</th><th>Reference No.</th><th>Amount</th><th>Received By</th><th>Notes</th><th>Download</th></tr></thead><tbody>{pageRows.map(p=><tr key={p.id}><td><div className="cell-with-icon"><div className="activity-icon"><IndianRupee size={15}/></div><b>{p.number}</b></div></td><td>{p.invoice?<button className="link-button" title="Open invoice" onClick={()=>navigate(`/invoices/${p.invoice!.id}`)}>{p.invoice.number}</button>:<span className="muted">#{p.invoice_id}</span>}</td><td>{shortDate(p.payment_date)}</td><td>{p.mode}</td><td>{p.reference_number||<span className="muted">--</span>}</td><td className="amount success"><b>{currency(p.amount,2)}</b></td><td>{p.received_by}</td><td>{p.notes||<span className="muted">--</span>}</td><td><button className="mini-button" title="Download receipt" onClick={()=>receipt(p)}><Download size={14}/></button></td></tr>)}{!rows.length&&<tr><td colSpan={9} className="muted">No payments recorded yet</td></tr>}</tbody></table></div>}<Pagination {...pageProps} noun="payments" /></Card></>}