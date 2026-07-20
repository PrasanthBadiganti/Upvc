import { useEffect, useState } from 'react';
import { Ban, Eye, Plus, RefreshCw, RotateCcw, Search } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import api from '../api';
import { Button, Card, Loading, PageHeader } from '../components/UI';
import Status from '../components/Status';
import { PurchaseBill } from '../types';
import { currency, shortDate } from '../utils';

export default function PurchaseBills(){
  const [rows,setRows]=useState<PurchaseBill[]>([]); const [loading,setLoading]=useState(true); const [search,setSearch]=useState(''); const navigate=useNavigate();
  const load=()=>{setLoading(true);api.get('/purchase-bills').then(r=>setRows(r.data)).finally(()=>setLoading(false));}; useEffect(load,[]);
  const cancel=async(b:PurchaseBill)=>{const paid=b.status==='Paid';if(!window.confirm(paid?'This purchase bill is fully paid. Cancel it anyway?':'Cancel this purchase bill?'))return;await api.post(`/purchase-bills/${b.id}/cancel`,null,{params:{force:paid}});load();};
  const reopen=async(b:PurchaseBill)=>{await api.post(`/purchase-bills/${b.id}/reopen`);load();};
  const filtered=rows.filter(b=>`${b.number} ${b.vendor_bill_number} ${b.vendor.name}`.toLowerCase().includes(search.toLowerCase()));
  return <>
    <PageHeader title="Purchase Bills" subtitle="Track what you owe vendors for stock and supplies" action={<Button onClick={()=>navigate('/purchase-bills/new')}><Plus size={15}/> New Purchase Bill</Button>} />
    <div className="list-toolbar"><div className="search-box"><Search size={16}/><input value={search} onChange={e=>setSearch(e.target.value)} placeholder="Search purchase bill, vendor or vendor bill no..."/></div><Button tone="secondary" onClick={load}><RefreshCw size={15}/> Refresh</Button></div>
    <Card className="list-card">{loading?<Loading/>:<div className="table-wrap"><table className="data-table"><thead><tr><th>PB No.</th><th>Vendor</th><th>Vendor Bill No.</th><th>Bill Date</th><th>Due Date</th><th>Grand Total</th><th>Paid</th><th>Pending</th><th>Status</th><th>Actions</th></tr></thead><tbody>{filtered.map(b=><tr key={b.id}><td className="cell-title">{b.number}</td><td>{b.vendor.name}<span className="cell-sub">{b.vendor.gst_number || '--'}</span></td><td>{b.vendor_bill_number || '--'}</td><td>{shortDate(b.bill_date)}</td><td>{shortDate(b.due_date)}</td><td className="amount"><b>{currency(b.grand_total,2)}</b></td><td className="amount success">{currency(b.paid_amount,2)}</td><td className="amount danger">{currency(b.pending_balance,2)}</td><td><Status value={b.status}/></td><td><div className="action-group"><button className="mini-button" title="View" onClick={()=>navigate(`/purchase-bills/${b.id}`)}><Eye size={14}/></button>{b.status==='Cancelled'?<button className="mini-button" title="Reopen" onClick={()=>reopen(b)}><RotateCcw size={14}/></button>:<button className="mini-button" title="Cancel" onClick={()=>cancel(b)}><Ban size={14}/></button>}</div></td></tr>)}
    {!filtered.length && <tr><td colSpan={10} className="muted">No purchase bills found</td></tr>}
    </tbody></table></div>}</Card>
  </>;
}
