import { FormEvent, useEffect, useState } from 'react';
import { CalendarPlus, Lock, Unlock } from 'lucide-react';
import api from '../api';
import { Button, Card, Field, Input, Loading, Modal, PageHeader } from '../components/UI';
import Status from '../components/Status';
import { FinancialYear } from '../types';
import { currency, shortDate } from '../utils';

type FyForm = { start_date: string; end_date: string; label: string };

const blank: FyForm = { start_date: '', end_date: '', label: '' };

export default function FinancialYears() {
  const [years, setYears] = useState<FinancialYear[]>([]);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState<FyForm>(blank);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const [busyId, setBusyId] = useState<number | null>(null);

  const load = () => { setLoading(true); api.get('/financial-years').then(r => setYears(r.data)).finally(() => setLoading(false)); };
  useEffect(load, []);

  const showAdd = () => { setForm(blank); setError(''); setOpen(true); };

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    setSaving(true);
    try {
      await api.post('/financial-years', form);
      setOpen(false);
      await load();
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Could not create this financial year');
    } finally {
      setSaving(false);
    }
  };

  const closeYear = async (fy: FinancialYear) => {
    if (!window.confirm(`Close ${fy.label}? This computes a final P&L/Balance Sheet snapshot and blocks new or edited postings dated within ${shortDate(fy.start_date)} - ${shortDate(fy.end_date)}.`)) return;
    setBusyId(fy.id);
    try {
      await api.post(`/financial-years/${fy.id}/close`);
      await load();
    } catch (err: any) {
      alert(err?.response?.data?.detail || 'Could not close this financial year');
    } finally {
      setBusyId(null);
    }
  };

  const reopenYear = async (fy: FinancialYear) => {
    if (!window.confirm(`Reopen ${fy.label}? This allows postings within this period again.`)) return;
    setBusyId(fy.id);
    try {
      await api.post(`/financial-years/${fy.id}/reopen`);
      await load();
    } catch (err: any) {
      alert(err?.response?.data?.detail || 'Could not reopen this financial year');
    } finally {
      setBusyId(null);
    }
  };

  return <>
    <PageHeader title="Financial Years" subtitle="Close a completed year to lock its books and snapshot its P&L / Balance Sheet" action={<Button onClick={showAdd}><CalendarPlus size={15} /> Add Financial Year</Button>} />
    <Card className="list-card">{loading ? <Loading /> : <div className="table-wrap"><table className="data-table"><thead><tr><th>Financial Year</th><th>Period</th><th>Status</th><th>Total Income</th><th>Total Expense</th><th>Net Profit</th><th>Closed On</th><th>Action</th></tr></thead><tbody>{years.map(fy => <tr key={fy.id}>
      <td className="cell-title">{fy.label}</td>
      <td>{shortDate(fy.start_date)} - {shortDate(fy.end_date)}</td>
      <td><Status value={fy.status} /></td>
      <td className="amount">{fy.total_income != null ? currency(fy.total_income, 2) : '--'}</td>
      <td className="amount">{fy.total_expense != null ? currency(fy.total_expense, 2) : '--'}</td>
      <td className={`amount ${Number(fy.net_profit) < 0 ? 'danger' : 'success'}`}><b>{fy.net_profit != null ? currency(fy.net_profit, 2) : '--'}</b></td>
      <td>{fy.closed_at ? shortDate(fy.closed_at) : '--'}</td>
      <td>{fy.status === 'Open'
        ? <button className="mini-button" title="Close Year" disabled={busyId === fy.id} onClick={() => closeYear(fy)}><Lock size={14} /></button>
        : <button className="mini-button" title="Reopen Year" disabled={busyId === fy.id} onClick={() => reopenYear(fy)}><Unlock size={14} /></button>}
      </td>
    </tr>)}
    {!years.length && <tr><td colSpan={8} className="muted">No financial years set up yet</td></tr>}
    </tbody></table></div>}</Card>

    <Modal open={open} onClose={() => setOpen(false)} title="Add Financial Year" width={480}>
      <form onSubmit={submit}>
        <div className="form-grid">
          <Field label="Start Date" required><Input type="date" required value={form.start_date} onChange={e => setForm({ ...form, start_date: e.target.value })} /></Field>
          <Field label="End Date" required><Input type="date" required value={form.end_date} onChange={e => setForm({ ...form, end_date: e.target.value })} /></Field>
          <Field label="Label (optional)"><Input placeholder="e.g. FY 2025-26" value={form.label} onChange={e => setForm({ ...form, label: e.target.value })} /></Field>
        </div>
        {error && <div className="toast">{error}</div>}
        <div className="form-actions"><Button type="button" tone="secondary" onClick={() => setOpen(false)}>Cancel</Button><Button type="submit" disabled={saving}>Save</Button></div>
      </form>
    </Modal>
  </>;
}
