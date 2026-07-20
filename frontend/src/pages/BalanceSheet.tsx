import { useEffect, useState } from 'react';
import api from '../api';
import { Button, Card, Field, Input, Loading, PageHeader } from '../components/UI';
import { currency } from '../utils';

type BsRow = { code: string; name: string; amount: number };
type BalanceSheet = { assets: BsRow[]; liabilities: BsRow[]; equity: BsRow[]; total_assets: number; total_liabilities: number; total_equity: number; balanced: boolean };

const today = () => new Date().toISOString().slice(0, 10);

export default function BalanceSheet() {
  const [asOf, setAsOf] = useState(today());
  const [data, setData] = useState<BalanceSheet | null>(null);
  const [loading, setLoading] = useState(true);

  const load = () => { setLoading(true); api.get('/balance-sheet', { params: { as_of: asOf } }).then(r => setData(r.data)).finally(() => setLoading(false)); };
  useEffect(load, []);

  return <>
    <PageHeader title="Balance Sheet" subtitle="Assets, liabilities and equity as of a date" />
    <Card className="settings-card">
      <div className="form-grid">
        <Field label="As Of Date"><Input type="date" value={asOf} onChange={e => setAsOf(e.target.value)} /></Field>
      </div>
      <div className="form-actions"><Button onClick={load}>Run Report</Button></div>
    </Card>

    {loading ? <Loading /> : data && <>
      <div className="report-grid">
        <Card className="list-card">
          <div className="card-head"><h3>Assets</h3></div>
          <div className="table-wrap"><table className="data-table"><thead><tr><th>Code</th><th>Account</th><th>Amount</th></tr></thead><tbody>{data.assets.map(row => <tr key={row.code}><td className="cell-title">{row.code}</td><td>{row.name}</td><td className="amount">{currency(row.amount, 2)}</td></tr>)}
          {!data.assets.length && <tr><td colSpan={3} className="muted">No asset balances</td></tr>}
          </tbody><tfoot><tr className="invoice-totals grand"><td colSpan={2}>Total Assets</td><td className="amount">{currency(data.total_assets, 2)}</td></tr></tfoot></table></div>
        </Card>
        <Card className="list-card">
          <div className="card-head"><h3>Liabilities</h3></div>
          <div className="table-wrap"><table className="data-table"><thead><tr><th>Code</th><th>Account</th><th>Amount</th></tr></thead><tbody>{data.liabilities.map(row => <tr key={row.code}><td className="cell-title">{row.code}</td><td>{row.name}</td><td className="amount">{currency(row.amount, 2)}</td></tr>)}
          {!data.liabilities.length && <tr><td colSpan={3} className="muted">No liability balances</td></tr>}
          </tbody><tfoot><tr className="invoice-totals"><td colSpan={2}>Total Liabilities</td><td className="amount">{currency(data.total_liabilities, 2)}</td></tr></tfoot></table></div>
          <div className="card-head" style={{ marginTop: 16 }}><h3>Equity</h3></div>
          <div className="table-wrap"><table className="data-table"><thead><tr><th>Code</th><th>Account</th><th>Amount</th></tr></thead><tbody>{data.equity.map(row => <tr key={row.code}><td className="cell-title">{row.code}</td><td>{row.name}</td><td className="amount">{currency(row.amount, 2)}</td></tr>)}
          {!data.equity.length && <tr><td colSpan={3} className="muted">No equity balances</td></tr>}
          </tbody><tfoot><tr className="invoice-totals grand"><td colSpan={2}>Total Liabilities + Equity</td><td className="amount">{currency(data.total_liabilities + data.total_equity, 2)}</td></tr></tfoot></table></div>
        </Card>
      </div>
      <Card className="settings-card"><div className="summary-line"><span>Status</span><span style={{ color: data.balanced ? '#0caf74' : '#e02424', fontWeight: 600 }}>{data.balanced ? 'Balanced' : 'Out of balance'}</span></div></Card>
    </>}
  </>;
}
