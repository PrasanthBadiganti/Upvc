import { useEffect, useState } from 'react';
import api from '../api';
import { Button, Card, Field, Input, Loading, PageHeader } from '../components/UI';
import { currency } from '../utils';

type AgingRow = { vendor_id: number; vendor_name: string; current: number; d1_30: number; d31_60: number; d61_90: number; d90_plus: number; total: number };
type Aging = { as_of: string; rows: AgingRow[]; totals: { current: number; d1_30: number; d31_60: number; d61_90: number; d90_plus: number; total: number } };

const today = () => new Date().toISOString().slice(0, 10);

export default function APAging() {
  const [asOf, setAsOf] = useState(today());
  const [data, setData] = useState<Aging | null>(null);
  const [loading, setLoading] = useState(true);

  const load = () => { setLoading(true); api.get('/ap-aging', { params: { as_of: asOf } }).then(r => setData(r.data)).finally(() => setLoading(false)); };
  useEffect(load, []);

  return <>
    <PageHeader title="Accounts Payable Aging" subtitle="Outstanding vendor bills grouped by how overdue they are" />
    <Card className="settings-card">
      <div className="form-grid">
        <Field label="As Of Date"><Input type="date" value={asOf} onChange={e => setAsOf(e.target.value)} /></Field>
      </div>
      <div className="form-actions"><Button onClick={load}>Run Report</Button></div>
    </Card>

    {loading ? <Loading /> : data && <Card className="list-card">
      <div className="table-wrap"><table className="data-table"><thead><tr><th>Vendor</th><th>Current</th><th>1-30 Days</th><th>31-60 Days</th><th>61-90 Days</th><th>90+ Days</th><th>Total</th></tr></thead><tbody>
        {data.rows.map(row => <tr key={row.vendor_id}>
          <td className="cell-title">{row.vendor_name}</td>
          <td className="amount">{currency(row.current, 2)}</td>
          <td className="amount">{currency(row.d1_30, 2)}</td>
          <td className="amount">{currency(row.d31_60, 2)}</td>
          <td className={`amount ${row.d61_90 > 0 ? 'danger' : ''}`}>{currency(row.d61_90, 2)}</td>
          <td className={`amount ${row.d90_plus > 0 ? 'danger' : ''}`}>{currency(row.d90_plus, 2)}</td>
          <td className="amount"><b>{currency(row.total, 2)}</b></td>
        </tr>)}
        {!data.rows.length && <tr><td colSpan={7} className="muted">No outstanding vendor bills</td></tr>}
      </tbody><tfoot><tr className="invoice-totals grand">
        <td>Total</td>
        <td className="amount">{currency(data.totals.current, 2)}</td>
        <td className="amount">{currency(data.totals.d1_30, 2)}</td>
        <td className="amount">{currency(data.totals.d31_60, 2)}</td>
        <td className="amount">{currency(data.totals.d61_90, 2)}</td>
        <td className="amount">{currency(data.totals.d90_plus, 2)}</td>
        <td className="amount">{currency(data.totals.total, 2)}</td>
      </tr></tfoot></table></div>
    </Card>}
  </>;
}
