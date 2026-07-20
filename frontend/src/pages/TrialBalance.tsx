import { useEffect, useMemo, useState } from 'react';
import api from '../api';
import { Card, Loading, PageHeader } from '../components/UI';
import { TrialBalanceRow } from '../types';
import { currency } from '../utils';

const groupOrder = ['Asset', 'Liability', 'Equity', 'Income', 'Expense'];

export default function TrialBalance() {
  const [rows, setRows] = useState<TrialBalanceRow[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => { api.get('/trial-balance').then(r => setRows(r.data)).finally(() => setLoading(false)); }, []);

  const totals = useMemo(() => ({
    debit: rows.reduce((s, r) => s + Number(r.debit), 0),
    credit: rows.reduce((s, r) => s + Number(r.credit), 0),
  }), [rows]);

  const sorted = useMemo(() => groupOrder.flatMap(type => rows.filter(r => r.account_type === type)), [rows]);
  const balanced = Math.abs(totals.debit - totals.credit) < 0.01;

  if (loading) return <Loading />;

  return <>
    <PageHeader title="Trial Balance" subtitle="Total debits and credits posted to every account" />
    <Card className="list-card">
      <div className="table-wrap"><table className="data-table"><thead><tr><th>Code</th><th>Account</th><th>Type</th><th>Debit</th><th>Credit</th></tr></thead><tbody>{sorted.map(row => <tr key={row.account_id}>
        <td className="cell-title">{row.code}</td>
        <td>{row.name}</td>
        <td>{row.account_type}</td>
        <td className="amount">{Number(row.debit) > 0 ? currency(row.debit, 2) : ''}</td>
        <td className="amount">{Number(row.credit) > 0 ? currency(row.credit, 2) : ''}</td>
      </tr>)}
      {!sorted.length && <tr><td colSpan={5} className="muted">No postings yet</td></tr>}
      </tbody><tfoot><tr className="invoice-totals grand"><td colSpan={3}>Total</td><td className="amount">{currency(totals.debit, 2)}</td><td className="amount">{currency(totals.credit, 2)}</td></tr></tfoot></table></div>
      <div className="summary-line" style={{ marginTop: 12 }}><span>Status</span><span style={{ color: balanced ? '#0caf74' : '#e02424', fontWeight: 600 }}>{balanced ? 'Balanced' : 'Out of balance'}</span></div>
    </Card>
  </>;
}
