import { useEffect, useState } from 'react';
import { FileDown, ReceiptText } from 'lucide-react';
import { useNavigate, useParams } from 'react-router-dom';
import api from '../api';
import { Button, Card, Loading, PageHeader } from '../components/UI';
import Status from '../components/Status';
import { Quotation } from '../types';
import { currency, shortDate } from '../utils';

export default function QuotationDetails(){
 const {id}=useParams(); const navigate=useNavigate(); const [q,setQ]=useState<Quotation|null>(null);
 useEffect(()=>{api.get(`/quotations/${id}`).then(r=>setQ(r.data));},[id]);
 if(!q)return <Loading/>;
 const convert=async()=>{const {data}=await api.post(`/quotations/${q.id}/convert`);navigate(`/invoices/${data.id}`)};
 return <><PageHeader title={`Quotation ${q.number}`} subtitle={`${q.customer.name}  -  ${shortDate(q.quotation_date)}`} action={<div className="action-group"><Button tone="secondary" onClick={()=>window.print()}><FileDown size={15}/> Print / PDF</Button><Button onClick={convert} disabled={q.status==='Converted'}><ReceiptText size={15}/> Convert to Invoice</Button></div>}/><Card className="list-card"><div className="card-head"><h3>Quotation Items</h3><Status value={q.status}/></div><div className="table-wrap"><table className="data-table"><thead><tr><th>#</th><th>Category</th><th>Style</th><th>Width</th><th>Height</th><th>SFT</th><th>Qty</th><th>Total SFT</th><th>Rate/SFT</th><th>Amount</th><th>Location</th></tr></thead><tbody>{q.items.map((i,x)=><tr key={x}><td>{x+1}</td><td>{i.category}</td><td>{i.style}</td><td>{i.width_mm}</td><td>{i.height_mm}</td><td>{i.sft}</td><td>{i.quantity}</td><td>{i.total_sft}</td><td>{currency(i.rate_per_sft,2)}</td><td>{currency(i.amount,2)}</td><td>{i.location}</td></tr>)}</tbody></table></div></Card><div className="report-grid" style={{marginTop:12}}><Card className="settings-card"><h3>Customer & Site</h3><p><b>{q.customer.name}</b></p><p>{q.address}</p><p>{q.site_location}</p></Card><Card className="settings-card"><h3>Commercial Summary</h3><div className="summary-line"><span>Subtotal</span><b>{currency(q.subtotal,2)}</b></div><div className="summary-line"><span>Transport</span><b>{currency(q.transport,2)}</b></div><div className="summary-line"><span>Discount</span><b>{currency(q.discount,2)}</b></div><div className="summary-line"><span>GST</span><b>{currency(q.gst,2)}</b></div><div className="summary-line total"><span>Grand Total</span><b>{currency(q.grand_total,2)}</b></div></Card></div></>;
}
