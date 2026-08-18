import { useEffect, useState } from 'react';
import { Copy, Edit3, Eye, FilePlus2, GitBranch, RefreshCw, Search } from 'lucide-react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import api from '../api';
import { Button, Card, Loading, PageHeader } from '../components/UI';
import Status from '../components/Status';
import { Quotation } from '../types';
import { currency, shortDate } from '../utils';
import Pagination, { usePagination } from '../components/Pagination';

export default function Quotations() {
  const [rows,setRows]=useState<Quotation[]>([]); const [loading,setLoading]=useState(true); const [search,setSearch]=useState('');
  const location=useLocation(); const navigate=useNavigate();
  const load=()=>{setLoading(true);api.get('/quotations').then(r=>setRows(r.data)).finally(()=>setLoading(false));};
  useEffect(load,[]);
  const convert=async(id:number)=>{const {data}=await api.post(`/quotations/${id}/convert`); navigate(`/invoices/${data.id}`);};
  const duplicate=async(id:number)=>{const {data}=await api.post(`/quotations/${id}/duplicate`); navigate(`/quotations/${data.id}/edit`);};
  const revise=async(id:number)=>{const {data}=await api.post(`/quotations/${id}/revise`); navigate(`/quotations/${data.id}/edit`);};
  const filtered=rows.filter(q=>`${q.number} ${q.customer.name}`.toLowerCase().includes(search.toLowerCase()));
  const { pageRows, props: pageProps } = usePagination(filtered);
  return <>
    <PageHeader title="Quotations" subtitle="Create, track and convert quotations" action={<Link to="/quotations/new"><Button><FilePlus2 size={16}/> Create Quotation</Button></Link>} toolbar={<><div className="search-box"><Search size={16}/><input value={search} onChange={e=>setSearch(e.target.value)} placeholder="Search quotation or customer..."/></div><Button tone="secondary" onClick={load}><RefreshCw size={15}/> Refresh</Button></>}/>
    {location.state?.created && <div className="toast">Quotation {location.state.created} created successfully</div>}
        <Card className="list-card">{loading?<Loading/>:<div className="table-wrap"><table className="data-table"><thead><tr><th>Quotation No.</th><th>Site / Location</th><th>Customer</th><th>Date</th><th>Validity</th><th>Items</th><th>Subtotal</th><th>GST</th><th>Grand Total</th><th>Status</th><th>Actions</th></tr></thead><tbody>{pageRows.map(q=><tr key={q.id}><td className="nowrap"><b>{q.number}</b></td><td title={q.site_location}>{q.site_location || <span className="muted">--</span>}</td><td>{q.customer.name}</td><td>{shortDate(q.quotation_date)}</td><td>{q.validity_days} Days</td><td>{q.items.length}</td><td className="amount">{currency(q.subtotal,2)}</td><td className="amount">{currency(q.gst,2)}</td><td className="amount"><b>{currency(q.grand_total,2)}</b></td><td><Status value={q.status}/></td><td><div className="action-group"><button className="mini-button" title="View" onClick={()=>navigate(`/quotations/${q.id}`)}><Eye size={14}/></button><button className="mini-button" title="Edit" disabled={['Accepted','Converted'].includes(q.status)} onClick={()=>navigate(`/quotations/${q.id}/edit`)}><Edit3 size={14}/></button><button className="mini-button" title="Duplicate" onClick={()=>duplicate(q.id)}><Copy size={14}/></button><button className="mini-button" title="Revise" onClick={()=>revise(q.id)}><GitBranch size={14}/></button><Button tone="ghost" onClick={()=>convert(q.id)} disabled={q.status==='Converted'}>Convert</Button></div></td></tr>)}</tbody></table></div>}<Pagination {...pageProps} noun="quotations" /></Card>
  </>;
}