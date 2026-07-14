import { useEffect, useState } from 'react';
import { IndianRupee } from 'lucide-react';
import api from '../api';
import { Card, Loading, PageHeader } from '../components/UI';
import { Payment } from '../types';
import { currency, shortDate } from '../utils';

export default function Payments(){const [rows,setRows]=useState<Payment[]>([]);const [loading,setLoading]=useState(true);useEffect(()=>{api.get('/payments').then(r=>setRows(r.data)).finally(()=>setLoading(false))},[]);return <><PageHeader title="Payments" subtitle="All customer collections and payment references"/><Card className="list-card">{loading?<Loading/>:<div className="table-wrap"><table className="data-table"><thead><tr><th>#</th><th>Invoice ID</th><th>Payment Date</th><th>Mode</th><th>Reference No.</th><th>Amount</th><th>Received By</th><th>Notes</th></tr></thead><tbody>{rows.map((p,i)=><tr key={p.id}><td><div className="activity-icon"><IndianRupee size={15}/></div></td><td>INV #{p.invoice_id}</td><td>{shortDate(p.payment_date)}</td><td>{p.mode}</td><td>{p.reference_number}</td><td className="amount success"><b>{currency(p.amount,2)}</b></td><td>{p.received_by}</td><td>{p.notes}</td></tr>)}</tbody></table></div>}</Card></>}
