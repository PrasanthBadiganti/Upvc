import { useEffect, useState } from 'react';
import api from '../api';
import { Button, Card, Field, Input, Loading, PageHeader } from '../components/UI';
import { currency } from '../utils';

type CfRow = { label: string; amount: number };
type CfSection = { rows: CfRow[]; total: number };
type CashFlow = {
  period: { from: string; to: string };
  operating_activities: CfSection;
  investing_activities: CfSection;
  financing_activities: CfSection;
  net_change_in_cash: number;
  opening_cash_balance: number;
  closing_cash_balance: number;
};

const firstOfMonth = () => { const d = new Date(); d.setDate(1); return d.toISOString().slice(0, 10); };
const today = () => new Date().toISOString().slice(0, 10);

const Section = ({ title, section }: { title: string; section: CfSection }) => (
  <Card className="list-card">
    <div className="card-head"><h3>{title}</h3></div>
    <div className="table-wrap"><table className="data-table"><thead><tr><th>Activity</th><th>Amount</th></tr></thead><tbody>
      {section.rows.map(row => <tr key={row.label}><td>{row.label}</td><td className={`amount ${row.amount < 0 ? 'danger' : 'success'}`}>{currency(row.amount, 2)}</td></tr>)}
      {!section.rows.length && <tr><td colSpan={2} className="muted">No activity in this period</td></tr>}
    </tbody><tfoot><tr className="invoice-totals grand"><td>Net Cash Flow</td><td className={`amount ${section.total < 0 ? 'danger' : 'success'}`}>{currency(section.total, 2)}</td></tr></tfoot></table></div>
  </Card>
);

export default function CashFlow() {
  const [fromDate, setFromDate] = useState(firstOfMonth());
  const [toDate, setToDate] = useState(today());
  const [data, setData] = useState<CashFlow | null>(null);
  const [loading, setLoading] = useState(true);

  const load = () => { setLoading(true); api.get('/cash-flow', { params: { from_date: fromDate, to_date: toDate } }).then(r => setData(r.data)).finally(() => setLoading(false)); };
  useEffect(load, []);

  return <>
    <PageHeader title="Cash Flow Statement" subtitle="Actual cash and bank movements, grouped by operating, investing and financing activity" />
    <Card className="settings-card">
      <div className="form-grid">
        <Field label="From Date"><Input type="date" value={fromDate} onChange={e => setFromDate(e.target.value)} /></Field>
        <Field label="To Date"><Input type="date" value={toDate} onChange={e => setToDate(e.target.value)} /></Field>
      </div>
      <div className="form-actions"><Button onClick={load}>Run Report</Button></div>
    </Card>

    {loading ? <Loading /> : data && <>
      <div className="report-grid">
        <Section title="Operating Activities" section={data.operating_activities} />
        <Section title="Investing Activities" section={data.investing_activities} />
        <Section title="Financing Activities" section={data.financing_activities} />
      </div>
      <Card className="settings-card">
        <div className="summary-line"><span>Opening Cash & Bank Balance</span><b>{currency(data.opening_cash_balance, 2)}</b></div>
        <div className="summary-line"><span>Net Change in Cash</span><b style={{ color: data.net_change_in_cash >= 0 ? '#0caf74' : '#e02424' }}>{currency(data.net_change_in_cash, 2)}</b></div>
        <div className="summary-line total"><span>Closing Cash & Bank Balance</span><b>{currency(data.closing_cash_balance, 2)}</b></div>
      </Card>
    </>}
  </>;
}
