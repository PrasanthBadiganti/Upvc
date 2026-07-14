import { useEffect, useState } from 'react';
import { Bar, BarChart, CartesianGrid, Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { FileText, IndianRupee, Percent, ReceiptText, UserRound, WalletCards } from 'lucide-react';
import api from '../api';
import { Card, Loading, PageHeader } from '../components/UI';
import MetricCard from '../components/MetricCard';
import Status from '../components/Status';
import { currency, shortDate } from '../utils';

type Report = {
  total_quote_value: number;
  total_invoice_value: number;
  received: number;
  pending: number;
  customer_status: Array<{ name: string; value: number }>;
  monthly: Array<{ month: string; quotation_value: number; invoice_value: number; received: number; pending: number }>;
  aging: Array<{ bucket: string; count: number; amount: number }>;
  top_pending: Array<{ customer: string; invoice_no: string; due_date: string; days_overdue: number; pending: number; status: string }>;
  salesperson_summary: Array<{ sales_person: string; quotation_count: number; quotation_value: number; invoice_count: number; invoice_value: number; received: number }>;
  conversion_summary: { quotation_count: number; converted_count: number; open_count: number; conversion_rate: number };
};

const palette = ['#3478f6', '#18b7a4', '#f59e0b', '#ef4444', '#8b5cf6'];

export default function Reports() {
  const [data, setData] = useState<Report | null>(null);
  useEffect(() => { api.get('/reports').then(r => setData(r.data)); }, []);
  if (!data) return <Loading />;

  return <>
    <PageHeader title="Reports" subtitle="Sales, quotation, invoice and collection performance" />
    <div className="report-grid">
      <MetricCard label="Total Quote Value" value={currency(data.total_quote_value)} icon={FileText} tone="blue" change={`${data.conversion_summary.quotation_count} quotations`} />
      <MetricCard label="Total Invoice Value" value={currency(data.total_invoice_value)} icon={ReceiptText} tone="teal" change={`${data.conversion_summary.converted_count} converted`} />
      <MetricCard label="Payments Received" value={currency(data.received)} icon={IndianRupee} tone="green" change="Collected to date" />
      <MetricCard label="Pending Collections" value={currency(data.pending)} icon={WalletCards} tone="red" change={`${data.top_pending.length} priority rows`} />
    </div>

    <div className="report-grid">
      <Card className="settings-card"><h3>Conversion Summary</h3><div className="summary-line"><span>Conversion Rate</span><b>{data.conversion_summary.conversion_rate}%</b></div><div className="summary-line"><span>Total Quotations</span><b>{data.conversion_summary.quotation_count}</b></div><div className="summary-line"><span>Converted</span><b>{data.conversion_summary.converted_count}</b></div><div className="summary-line"><span>Open</span><b>{data.conversion_summary.open_count}</b></div></Card>
      <Card className="settings-card"><h3>Customer Mix</h3>{data.customer_status.map((row, i) => <div className="summary-line" key={row.name}><span><UserRound size={13} color={palette[i % palette.length]} /> {row.name}</span><b>{row.value}</b></div>)}</Card>
      <Card className="settings-card"><h3>Aging Snapshot</h3>{data.aging.map((row, i) => <div className="summary-line" key={row.bucket}><span><Percent size={13} color={palette[i % palette.length]} /> {row.bucket}</span><b>{currency(row.amount, 0)}</b></div>)}</Card>
    </div>

    <div className="report-charts">
      <Card className="chart-card"><div className="chart-title"><h3>Monthly Financial Trend</h3></div><ResponsiveContainer width="100%" height={320}><BarChart data={data.monthly} margin={{ top: 10, right: 14, left: 0, bottom: 0 }}><CartesianGrid stroke="#edf1f5" vertical={false} /><XAxis dataKey="month" tick={{ fontSize: 10 }} /><YAxis tick={{ fontSize: 10 }} tickFormatter={v => `${Math.round(Number(v) / 1000)}k`} /><Tooltip formatter={v => currency(Number(v), 0)} /><Legend /><Bar dataKey="quotation_value" name="Quotes" fill="#3478f6" radius={[4, 4, 0, 0]} /><Bar dataKey="invoice_value" name="Invoices" fill="#18b7a4" radius={[4, 4, 0, 0]} /><Bar dataKey="received" name="Received" fill="#f59e0b" radius={[4, 4, 0, 0]} /></BarChart></ResponsiveContainer></Card>
      <Card className="chart-card"><div className="chart-title"><h3>Collection Aging</h3></div><ResponsiveContainer width="100%" height={320}><PieChart><Pie data={data.aging} dataKey="amount" nameKey="bucket" innerRadius={68} outerRadius={112}>{data.aging.map((_, i) => <Cell key={i} fill={palette[i % palette.length]} />)}</Pie><Tooltip formatter={v => currency(Number(v), 0)} /><Legend /></PieChart></ResponsiveContainer></Card>
    </div>

    <div className="report-charts">
      <Card className="list-card"><div className="card-head"><h3>Top Pending Collections</h3></div><div className="table-wrap"><table className="data-table"><thead><tr><th>Customer</th><th>Invoice</th><th>Due Date</th><th>Age</th><th>Pending</th><th>Status</th></tr></thead><tbody>{data.top_pending.length ? data.top_pending.map(row => <tr key={row.invoice_no}><td>{row.customer}</td><td>{row.invoice_no}</td><td>{shortDate(row.due_date)}</td><td>{row.days_overdue ? `${row.days_overdue} days` : 'Current'}</td><td className="amount">{currency(row.pending, 2)}</td><td><Status value={row.status} /></td></tr>) : <tr><td colSpan={6} className="muted">No pending collections</td></tr>}</tbody></table></div></Card>
      <Card className="list-card"><div className="card-head"><h3>Salesperson Performance</h3></div><div className="table-wrap"><table className="data-table"><thead><tr><th>Salesperson</th><th>Quotes</th><th>Quote Value</th><th>Invoices</th><th>Invoice Value</th><th>Received</th></tr></thead><tbody>{data.salesperson_summary.map(row => <tr key={row.sales_person}><td>{row.sales_person}</td><td>{row.quotation_count}</td><td className="amount">{currency(row.quotation_value, 0)}</td><td>{row.invoice_count}</td><td className="amount">{currency(row.invoice_value, 0)}</td><td className="amount success">{currency(row.received, 0)}</td></tr>)}</tbody></table></div></Card>
    </div>
  </>;
}
