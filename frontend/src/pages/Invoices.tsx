import { useEffect, useState } from 'react';
import { Ban, Eye, RefreshCw, RotateCcw, Search } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import api from '../api';
import { Button, Card, Loading, PageHeader } from '../components/UI';
import Status from '../components/Status';
import { Invoice } from '../types';
import { currency, shortDate } from '../utils';
import { useToastContext } from '../contexts/ToastContext';
import { ConfirmDialog } from '../components/ConfirmDialog';
import { EmptyState } from '../components/EmptyState';
import Pagination, { usePagination } from '../components/Pagination';

export default function Invoices(){
  const [rows,setRows]=useState<Invoice[]>([]);
  const [loading,setLoading]=useState(true);
  const [search,setSearch]=useState('');
  const navigate=useNavigate();
  const toast = useToastContext();
  const [confirmOpen,setConfirmOpen]=useState(false);
  const [confirmInvoice,setConfirmInvoice]=useState<Invoice|null>(null);
  const [confirmLoading,setConfirmLoading]=useState(false);

  const load=()=>{setLoading(true);api.get('/invoices').then(r=>setRows(r.data)).finally(()=>setLoading(false));};
  useEffect(load,[]);

  const handleCancel = (invoice: Invoice) => {
    setConfirmInvoice(invoice);
    setConfirmOpen(true);
  };

  const confirmCancel = async () => {
    if (!confirmInvoice) return;
    setConfirmLoading(true);
    try {
      const paid = confirmInvoice.status === 'Paid';
      await api.post(`/invoices/${confirmInvoice.id}/cancel`, null, { params: { force: paid } });
      toast.success('Invoice cancelled successfully');
      await load();
      setConfirmOpen(false);
      setConfirmInvoice(null);
    } catch (err) {
      toast.error('Failed to cancel invoice');
    } finally {
      setConfirmLoading(false);
    }
  };

  const reopen = async (i: Invoice) => {
    try {
      await api.post(`/invoices/${i.id}/reopen`);
      toast.success('Invoice reopened successfully');
      await load();
    } catch (err) {
      toast.error('Failed to reopen invoice');
    }
  };

  const filtered = rows.filter(i => `${i.number} ${i.customer.name}`.toLowerCase().includes(search.toLowerCase()));

  const { pageRows, props: pageProps } = usePagination(filtered);

  return <>
    <PageHeader title="Invoices" subtitle="Track invoices, due dates and collections"  toolbar={<><div className="search-box"><Search size={16} /><input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search invoice or customer..." /></div><Button tone="secondary" onClick={load}><RefreshCw size={15} /> Refresh</Button></>}/>
        <Card className="list-card">{loading ? <Loading /> : filtered.length === 0 ? <EmptyState icon="📄" title="No Invoices" description="Create your first invoice from a quotation or start a new one." action={{ label: '+ Create Invoice', onClick: () => navigate('/invoices') }} /> : <div className="table-wrap"><table className="data-table"><thead><tr><th>Invoice No.</th><th>Customer</th><th>Project / Site</th><th>Invoice Date</th><th>Due Date</th><th>Grand Total</th><th>Paid</th><th>Pending</th><th>Status</th><th>Actions</th></tr></thead><tbody>{pageRows.map(i => <tr key={i.id}><td className="cell-title">{i.number}</td><td title={i.customer.name}><b>{i.customer.name}</b></td><td title={i.customer.project_site}>{i.customer.project_site || <span className="muted">--</span>}</td><td>{shortDate(i.invoice_date)}</td><td>{shortDate(i.due_date)}</td><td className="amount"><b>{currency(i.grand_total, 2)}</b></td><td className="amount success">{currency(i.paid_amount, 2)}</td><td className="amount danger">{currency(i.pending_balance, 2)}</td><td><Status value={i.status} /></td><td><div className="action-group"><button className="mini-button" title="View details" onClick={() => navigate(`/invoices/${i.id}`)}><Eye size={14} /></button>{i.status === 'Cancelled' ? <button className="mini-button" title="Reopen" onClick={() => reopen(i)}><RotateCcw size={14} /></button> : <button className="mini-button" title="Cancel" onClick={() => handleCancel(i)}><Ban size={14} /></button>}</div></td></tr>)}</tbody></table></div>}<Pagination {...pageProps} noun="invoices" /></Card>
    <ConfirmDialog
      open={confirmOpen}
      title="Cancel Invoice?"
      message={confirmInvoice?.status === 'Paid' ? 'This invoice is fully paid. Are you sure you want to cancel it?' : 'This will cancel the invoice and block future payments. Continue?'}
      isDangerous={true}
      confirmLabel="Yes, Cancel"
      onConfirm={confirmCancel}
      onCancel={() => { setConfirmOpen(false); setConfirmInvoice(null); }}
      isLoading={confirmLoading}
    />
  </>;
}