import { useEffect, useState } from 'react';
import { Ban, Eye, RefreshCw, Search } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import api from '../api';
import { Button, Card, Loading, PageHeader } from '../components/UI';
import Status from '../components/Status';
import { CreditNote } from '../types';
import { currency, shortDate } from '../utils';

export default function CreditNotes(){
  const [rows,setRows]=useState<CreditNote[]>([]); const [loading,setLoading]=useState(true); const [search,setSearch]=useState(''); const navigate=useNavigate();
  const load=()=>{setLoading(true);api.get('/credit-notes').then(r=>setRows(r.data)).finally(()=>setLoading(false));}; useEffect(load,[]);
  const cancel=async(n:CreditNote)=>{if(!window.confirm('Cancel this credit note? The invoice balance will be restored.'))return;await api.post(`/credit-notes/${n.id}/cancel`);load();};
  const filtered=rows.filter(n=>`${n.number} ${n.customer.name} ${n.invoice.number}`.toLowerCase().includes(search.toLowerCase()));
  return <>
    <PageHeader title="Credit Notes" subtitle="Sales returns and adjustments issued against invoices"/>
    <div className="list-toolbar"><div className="search-box"><Search size={16}/><input value={search} onChange={e=>setSearch(e.target.value)} placeholder="Search credit note, customer or invoice..."/></div><Button tone="secondary" onClick={load}><RefreshCw size={15}/> Refresh</Button></div>
    <Card className="list-card">{loading?<Loading/>:<div className="table-wrap"><table className="data-table"><thead><tr><th>Credit Note No.</th><th>Customer</th><th>Against Invoice</th><th>Note Date</th><th>Reason</th><th>Total</th><th>Status</th><th>Actions</th></tr></thead><tbody>{filtered.map(n=><tr key={n.id}><td className="cell-title">{n.number}</td><td>{n.customer.name}</td><td>{n.invoice.number}</td><td>{shortDate(n.note_date)}</td><td>{n.reason || '--'}</td><td className="amount"><b>{currency(n.grand_total,2)}</b></td><td><Status value={n.status}/></td><td><div className="action-group"><button className="mini-button" title="View" onClick={()=>navigate(`/credit-notes/${n.id}`)}><Eye size={14}/></button>{n.status!=='Cancelled'&&<button className="mini-button" title="Cancel" onClick={()=>cancel(n)}><Ban size={14}/></button>}</div></td></tr>)}
    {!filtered.length && <tr><td colSpan={8} className="muted">No credit notes found</td></tr>}
    </tbody></table></div>}</Card>
  </>;
}
