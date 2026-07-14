import { useEffect, useState } from 'react';
import { Eye, RefreshCw, Search } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import api from '../api';
import { Button, Card, Loading, PageHeader } from '../components/UI';
import Status from '../components/Status';
import { Invoice } from '../types';
import { currency, shortDate } from '../utils';

export default function Invoices(){
  const [rows,setRows]=useState<Invoice[]>([]); const [loading,setLoading]=useState(true); const [search,setSearch]=useState(''); const navigate=useNavigate();
  const load=()=>{setLoading(true);api.get('/invoices').then(r=>setRows(r.data)).finally(()=>setLoading(false));}; useEffect(load,[]);
  const filtered=rows.filter(i=>`${i.number} ${i.customer.name}`.toLowerCase().includes(search.toLowerCase()));
  return <><PageHeader title="Invoices" subtitle="Track invoices, due dates and collections"/><div className="list-toolbar"><div className="search-box"><Search size={16}/><input value={search} onChange={e=>setSearch(e.target.value)} placeholder="Search invoice or customer..."/></div><Button tone="secondary" onClick={load}><RefreshCw size={15}/> Refresh</Button></div><Card className="list-card">{loading?<Loading/>:<div className="table-wrap"><table className="data-table"><thead><tr><th>Invoice No.</th><th>Customer</th><th>Invoice Date</th><th>Due Date</th><th>Grand Total</th><th>Paid</th><th>Pending</th><th>Status</th><th>Quotation</th><th>Actions</th></tr></thead><tbody>{filtered.map(i=><tr key={i.id}><td className="cell-title">{i.number}</td><td>{i.customer.name}<span className="cell-sub">{i.customer.project_site}</span></td><td>{shortDate(i.invoice_date)}</td><td>{shortDate(i.due_date)}</td><td className="amount"><b>{currency(i.grand_total,2)}</b></td><td className="amount success">{currency(i.paid_amount,2)}</td><td className="amount danger">{currency(i.pending_balance,2)}</td><td><Status value={i.status}/></td><td>{i.quotation?.number||'—'}</td><td><button className="mini-button" onClick={()=>navigate(`/invoices/${i.id}`)}><Eye size={14}/></button></td></tr>)}</tbody></table></div>}</Card></>;
}
