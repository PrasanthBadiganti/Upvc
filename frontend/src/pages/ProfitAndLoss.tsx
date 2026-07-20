import { useEffect, useState } from 'react';
import api from '../api';
import { Button, Card, Field, Input, Loading, PageHeader } from '../components/UI';
import { currency } from '../utils';

type PnlRow = { code: string; name: string; amount: number };
type Pnl = { income: PnlRow[]; expenses: PnlRow[]; total_income: number; total_expense: number; net_profit: number };

const firstOfMonth = () => { const d = new Date(); d.setDate(1); return d.toISOString().slice(0, 10); };
const today = () => new Date().toISOString().slice(0, 10);

export default function ProfitAndLoss() {
  const [fromDate, setFromDate] = useState(firstOfMonth());
  const [toDate, setToDate] = useState(today());
  const [data, setData] = useState<Pnl | null>(null);
  const [loading, setLoading] = useState(true);

  const load = () => { setLoading(true); api.get('/profit-and-loss', { params: { from_date: fromDate, to_date: toDate } }).then(r => setData(r.data)).finally(() => setLoading(false)); };
  useEffect(load, []);

  return <>
    <PageHeader title="Profit &amp; Loss" subtitle="Income and expenses for the selected period" />
    <Card className="settings-card">
      <div className="form-grid">
        <Field label="From Date"><Input type="date" value={fromDate} onChange={e => setFromDate(e.target.value)} /></Field>
        <Field label="To Date"><Input type="date" value={toDate} onChange={e => setToDate(e.target.value)} /></Field>
      </div>
      <div className="form-actions"><Button onClick={load}>Run Report</Button></div>
    </Card>

    {loading ? <Loading /> : data && <div className="report-grid">
      <Card className="list-card">
        <div className="card-head"><h3>Income</h3></div>
        <div className="table-wrap"><table className="data-table"><thead><tr><th>Code</th><th>Account</th><th>Amount</th></tr></thead><tbody>{data.income.map(row => <tr key={row.code}><td className="cell-title">{row.code}</td><td>{row.name}</td><td className="amount">{currency(row.amount, 2)}</td></tr>)}
        {!data.income.length && <tr><td colSpan={3} className="muted">No income posted in this period</td></tr>}
        </tbody><tfoot><tr className="invoice-totals grand"><td colSpan={2}>Total Income</td><td className="amount">{currency(data.total_income, 2)}</td></tr></tfoot></table></div>
      </Card>
      <Card className="list-card">
        <div className="card-head"><h3>Expenses</h3></div>
        <div className="table-wrap"><table className="data-table"><thead><tr><th>Code</th><th>Account</th><th>Amount</th></tr></thead><tbody>{data.expenses.map(row => <tr key={row.code}><td className="cell-title">{row.code}</td><td>{row.name}</td><td className="amount">{currency(row.amount, 2)}</td></tr>)}
        {!data.expenses.length && <tr><td colSpan={3} className="muted">No expenses posted in this period</td></tr>}
        </tbody><tfoot><tr className="invoice-totals grand"><td colSpan={2}>Total Expenses</td><td className="amount">{currency(data.total_expense, 2)}</td></tr></tfoot></table></div>
      </Card>
      <Card className="settings-card"><h3>Net Result</h3><div className="summary-line total"><span>{data.net_profit >= 0 ? 'Net Profit' : 'Net Loss'}</span><b style={{ color: data.net_profit >= 0 ? '#0caf74' : '#e02424' }}>{currency(Math.abs(data.net_profit), 2)}</b></div></Card>
    </div>}
  </>;
}
