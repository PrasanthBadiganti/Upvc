import { FormEvent, useEffect, useState } from 'react';
import { Plus, Trash2 } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import api from '../api';
import { Button, Card, Field, Input, PageHeader, Select } from '../components/UI';
import { ChartOfAccount } from '../types';
import { currency } from '../utils';

type Row = { account_id: number | ''; debit: string; credit: string };

const blankRow = (): Row => ({ account_id: '', debit: '', credit: '' });

export default function ManualJournalEntry() {
  const navigate = useNavigate();
  const [accounts, setAccounts] = useState<ChartOfAccount[]>([]);
  const [entryDate, setEntryDate] = useState(new Date().toISOString().slice(0, 10));
  const [narration, setNarration] = useState('');
  const [rows, setRows] = useState<Row[]>([blankRow(), blankRow()]);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => { api.get('/accounts').then(r => setAccounts(r.data)); }, []);

  const setRow = (i: number, patch: Partial<Row>) => setRows(rows.map((r, idx) => idx === i ? { ...r, ...patch } : r));
  const addRow = () => setRows([...rows, blankRow()]);
  const removeRow = (i: number) => setRows(rows.filter((_, idx) => idx !== i));

  const totalDebit = rows.reduce((s, r) => s + (Number(r.debit) || 0), 0);
  const totalCredit = rows.reduce((s, r) => s + (Number(r.credit) || 0), 0);
  const nonzeroRows = rows.filter(r => (Number(r.debit) || 0) > 0 || (Number(r.credit) || 0) > 0);
  const balanced = totalDebit === totalCredit && totalDebit > 0;
  const canSubmit = balanced && nonzeroRows.length >= 2 && nonzeroRows.every(r => r.account_id !== '') && narration.trim() !== '';

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    setSaving(true);
    try {
      const { data } = await api.post('/journal/manual', {
        entry_date: entryDate,
        narration,
        lines: nonzeroRows.map(r => ({ account_id: r.account_id, debit: r.debit || '0', credit: r.credit || '0' })),
      });
      navigate(`/journal/${data.id}`);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Could not save this journal entry');
    } finally {
      setSaving(false);
    }
  };

  return <>
    <PageHeader title="New Manual Journal Entry" subtitle="Record a correction or accrual directly against the ledger" />
    <Card className="settings-card">
      <form onSubmit={submit}>
        <div className="form-grid">
          <Field label="Entry Date" required><Input type="date" required value={entryDate} onChange={e => setEntryDate(e.target.value)} /></Field>
          <Field label="Narration" required><Input required value={narration} onChange={e => setNarration(e.target.value)} placeholder="e.g. Accrual for July electricity bill" /></Field>
        </div>

        <div className="table-wrap" style={{ marginTop: 12 }}>
          <table className="data-table">
            <thead><tr><th>Account</th><th>Debit</th><th>Credit</th><th /></tr></thead>
            <tbody>
              {rows.map((row, i) => <tr key={i}>
                <td>
                  <Select value={row.account_id} onChange={e => setRow(i, { account_id: e.target.value ? Number(e.target.value) : '' })}>
                    <option value="">Select account</option>
                    {accounts.map(a => <option key={a.id} value={a.id}>{a.code} - {a.name}</option>)}
                  </Select>
                </td>
                <td><Input type="number" min="0" step="0.01" value={row.debit} onChange={e => setRow(i, { debit: e.target.value, credit: e.target.value ? '' : row.credit })} /></td>
                <td><Input type="number" min="0" step="0.01" value={row.credit} onChange={e => setRow(i, { credit: e.target.value, debit: e.target.value ? '' : row.debit })} /></td>
                <td><button type="button" className="mini-button" disabled={rows.length <= 2} onClick={() => removeRow(i)}><Trash2 size={14} /></button></td>
              </tr>)}
              <tr className="invoice-totals grand">
                <td>Total</td>
                <td className="amount">{currency(totalDebit, 2)}</td>
                <td className="amount">{currency(totalCredit, 2)}</td>
                <td />
              </tr>
            </tbody>
          </table>
        </div>

        <div className="form-actions" style={{ justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <Button type="button" tone="secondary" onClick={addRow}><Plus size={14} /> Add Line</Button>
            <span style={{ marginLeft: 12, color: balanced ? '#0f9d58' : '#d93025', fontWeight: 600 }}>{balanced ? 'Balanced' : 'Not Balanced'}</span>
          </div>
          <div>
            <Button type="button" tone="secondary" onClick={() => navigate('/journal')} style={{ marginRight: 8 }}>Cancel</Button>
            <Button type="submit" disabled={!canSubmit || saving}>Post Journal Entry</Button>
          </div>
        </div>
        {error && <div className="toast" style={{ marginTop: 12 }}>{error}</div>}
      </form>
    </Card>
  </>;
}
