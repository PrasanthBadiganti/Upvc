import { FormEvent, useEffect, useState } from 'react';
import { Boxes, CalendarDays, IndianRupee, LineChart, Trash2 } from 'lucide-react';
import { useParams } from 'react-router-dom';
import api from '../api';
import { Button, Card, Field, Input, Loading, Modal, PageHeader } from '../components/UI';
import Status from '../components/Status';
import { FixedAsset } from '../types';
import { currency, shortDate } from '../utils';

export default function FixedAssetDetails() {
  const { id } = useParams();
  const [asset, setAsset] = useState<FixedAsset | null>(null);
  const [depOpen, setDepOpen] = useState(false);
  const [disposeOpen, setDisposeOpen] = useState(false);
  const [asOfDate, setAsOfDate] = useState(new Date().toISOString().slice(0, 10));
  const [disposal, setDisposal] = useState({ disposal_date: new Date().toISOString().slice(0, 10), disposal_value: 0 });
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);

  const load = () => api.get(`/fixed-assets/${id}`).then(r => setAsset(r.data));
  useEffect(() => { load(); }, [id]);
  if (!asset) return <Loading />;

  const bookValue = Number(asset.purchase_cost) - Number(asset.accumulated_depreciation);
  const active = asset.status === 'Active';

  const runDepreciation = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    setSaving(true);
    try {
      await api.post(`/fixed-assets/${asset.id}/depreciate`, { as_of_date: asOfDate });
      setDepOpen(false);
      await load();
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Could not record depreciation');
    } finally {
      setSaving(false);
    }
  };

  const dispose = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    setSaving(true);
    try {
      await api.post(`/fixed-assets/${asset.id}/dispose`, disposal);
      setDisposeOpen(false);
      await load();
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Could not dispose this asset');
    } finally {
      setSaving(false);
    }
  };

  return <>
    <PageHeader title="Fixed Asset Details" action={active ? <div className="action-group"><Button tone="secondary" onClick={() => { setError(''); setDepOpen(true); }}><LineChart size={15} /> Run Depreciation</Button><Button tone="danger" onClick={() => { setError(''); setDisposeOpen(true); }}><Trash2 size={15} /> Dispose Asset</Button></div> : undefined} />
    <div className="metric-grid invoice-summary-cards">
      <Card className="invoice-summary-card"><div className="metric-icon blue"><Boxes size={18} /></div><div><small>Asset</small><strong>{asset.name}</strong><em style={{ color: '#60708a' }}>{asset.code} - {asset.category}</em></div></Card>
      <Card className="invoice-summary-card"><div className="metric-icon blue"><CalendarDays size={18} /></div><div><small>Purchase Date</small><strong>{shortDate(asset.purchase_date)}</strong></div></Card>
      <Card className="invoice-summary-card"><div className="metric-icon blue"><IndianRupee size={18} /></div><div><small>Purchase Cost</small><strong>{currency(asset.purchase_cost, 2)}</strong></div></Card>
      <Card className="invoice-summary-card"><div className="metric-icon red"><IndianRupee size={18} /></div><div><small>Accumulated Depreciation</small><strong>{currency(asset.accumulated_depreciation, 2)}</strong></div></Card>
      <Card className="invoice-summary-card"><div className="metric-icon green"><IndianRupee size={18} /></div><div><small>Book Value</small><strong>{currency(bookValue, 2)}</strong></div></Card>
      <Card className="invoice-summary-card"><div className="metric-icon green"><IndianRupee size={18} /></div><div><small>Status</small><strong><Status value={asset.status} /></strong></div></Card>
    </div>

    <Card className="invoice-table-card">
      <div className="card-head"><h3>Asset Details</h3></div>
      <div className="form-grid" style={{ padding: '0 16px 16px' }}>
        <div><small>Depreciation Method</small><div><b>{asset.depreciation_method}{asset.depreciation_method === 'Written Down Value' ? ` (${asset.depreciation_rate}% p.a.)` : ''}</b></div></div>
        <div><small>Useful Life</small><div><b>{asset.useful_life_years} years</b></div></div>
        <div><small>Salvage Value</small><div><b>{currency(asset.salvage_value, 2)}</b></div></div>
        <div><small>Vendor</small><div><b>{asset.vendor?.name || '--'}</b></div></div>
        <div><small>Location</small><div><b>{asset.location || '--'}</b></div></div>
        {asset.status === 'Disposed' && <>
          <div><small>Disposal Date</small><div><b>{shortDate(asset.disposal_date)}</b></div></div>
          <div><small>Disposal Value</small><div><b>{currency(asset.disposal_value, 2)}</b></div></div>
        </>}
      </div>
    </Card>

    <Card className="invoice-table-card">
      <div className="card-head"><h3>Depreciation History</h3></div>
      <div className="table-wrap"><table className="data-table"><thead><tr><th>Period Start</th><th>Period End</th><th>Amount</th><th>Book Value After</th></tr></thead><tbody>
        {asset.depreciation_entries.map(entry => <tr key={entry.id}>
          <td>{shortDate(entry.period_start)}</td>
          <td>{shortDate(entry.period_end)}</td>
          <td className="amount">{currency(entry.amount, 2)}</td>
          <td className="amount"><b>{currency(entry.book_value_after, 2)}</b></td>
        </tr>)}
        {!asset.depreciation_entries.length && <tr><td colSpan={4} className="muted">No depreciation recorded yet</td></tr>}
      </tbody></table></div>
    </Card>

    <Modal open={depOpen} onClose={() => setDepOpen(false)} title="Run Depreciation" width={480}>
      <form onSubmit={runDepreciation}>
        <div className="form-grid">
          <Field label="As Of Date" required><Input type="date" required value={asOfDate} onChange={e => setAsOfDate(e.target.value)} /></Field>
        </div>
        {error && <div className="toast">{error}</div>}
        <div className="form-actions"><Button type="button" tone="secondary" onClick={() => setDepOpen(false)}>Cancel</Button><Button type="submit" disabled={saving}>Post Depreciation</Button></div>
      </form>
    </Modal>

    <Modal open={disposeOpen} onClose={() => setDisposeOpen(false)} title="Dispose Asset" width={480}>
      <form onSubmit={dispose}>
        <div className="form-grid">
          <Field label="Disposal Date" required><Input type="date" required value={disposal.disposal_date} onChange={e => setDisposal({ ...disposal, disposal_date: e.target.value })} /></Field>
          <Field label="Disposal Value" required><Input type="number" step="0.01" min="0" required value={disposal.disposal_value} onChange={e => setDisposal({ ...disposal, disposal_value: Number(e.target.value) })} /></Field>
        </div>
        {error && <div className="toast">{error}</div>}
        <div className="form-actions"><Button type="button" tone="secondary" onClick={() => setDisposeOpen(false)}>Cancel</Button><Button type="submit" tone="danger" disabled={saving}>Confirm Disposal</Button></div>
      </form>
    </Modal>
  </>;
}
