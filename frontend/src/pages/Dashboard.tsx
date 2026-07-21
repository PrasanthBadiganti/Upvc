import { useEffect, useState } from 'react';
import { Bar, BarChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { BellRing, FilePlus2, IndianRupee, ReceiptText, UserPlus2, UsersRound, WalletCards } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import api from '../api';
import { Card, Loading, PageHeader } from '../components/UI';
import MetricCard from '../components/MetricCard';
import Status from '../components/Status';
import { currency, shortDate } from '../utils';

const pct = (part: number, whole: number) => (whole > 0 ? Math.round((part / whole) * 100) : 0);

const quotationTrend = (thisMonth: number, lastMonth: number) => {
  if (lastMonth === 0) return thisMonth > 0 ? 'New this month' : undefined;
  const change = Math.round(((thisMonth - lastMonth) / lastMonth) * 100);
  return `${change >= 0 ? '+' : ''}${change}% vs last month`;
};

type DashboardData = {
  metrics: Record<string, number>;
  monthly: Array<Record<string, number | string>>;
  customer_status: Array<{ name: string; value: number }>;
  pending_payments: Array<{ customer: string; invoice_no: string; due_date: string; balance: number; status: string }>;
  today_followups: Array<{ time: string; customer: string; purpose: string; channel: string }>;
  recent_activity: Array<{ type: string; title: string; detail: string; when: string }>;
};

const PIE_COLORS = ['#18b7a4', '#f59e0b', '#3478f6', '#ef4444'];

export default function Dashboard() {
  const [data, setData] = useState<DashboardData | null>(null);
  const navigate = useNavigate();
  useEffect(() => { api.get('/dashboard').then(r => setData(r.data)); }, []);
  if (!data) return <Loading />;
  const m = data.metrics;
  return (
    <>
      <PageHeader title="Dashboard" subtitle="Overview of your business performance" />
      <div className="metric-grid dashboard-metrics">
        <MetricCard label="Total Leads" value={m.total_leads} change={`${m.new_leads_this_month} new this month`} icon={UserPlus2} tone="blue" />
        <MetricCard label="Live Customers" value={m.live_customers} change={`${pct(m.live_customers, m.total_leads)}% of leads`} icon={UsersRound} tone="teal" />
        <MetricCard label="Pending Customers" value={m.pending_customers} change={`${pct(m.pending_customers, m.total_leads)}% of leads`} icon={BellRing} tone="amber" />
        <MetricCard label="Quotations This Month" value={m.quotations_this_month} change={quotationTrend(m.quotations_this_month, m.quotations_last_month)} icon={FilePlus2} tone="blue" />
        <MetricCard label="Pending Payments" value={currency(m.pending_payments)} change={`Across ${m.pending_invoice_count} invoice${m.pending_invoice_count === 1 ? '' : 's'}`} icon={WalletCards} tone="red" />
        <MetricCard label="Revenue Received" value={currency(m.revenue_received)} change={`${pct(m.revenue_received, m.revenue_received + m.pending_payments)}% collected`} icon={IndianRupee} tone="teal" />
      </div>

      <div className="dashboard-grid">
        <Card className="chart-card">
          <div className="chart-title"><div><h3>Quotations vs Invoices (Monthly)</h3><div className="chart-legend"><span><i className="legend-dot" style={{background:'#3478f6'}} />Quotations</span><span><i className="legend-dot" style={{background:'#18b7a4'}} />Invoices</span></div></div><button className="button secondary">Last 12 Months</button></div>
          <ResponsiveContainer width="100%" height={210}>
            <BarChart data={data.monthly} barGap={2} margin={{ top: 15, right: 4, left: -20, bottom: 0 }}>
              <CartesianGrid stroke="#edf1f5" vertical={false} />
              <XAxis dataKey="month" tick={{fontSize:9,fill:'#60708a'}} axisLine={false} tickLine={false} />
              <YAxis tick={{fontSize:9,fill:'#60708a'}} axisLine={false} tickLine={false} />
              <Tooltip />
              <Bar dataKey="quotations" fill="#3478f6" radius={[2,2,0,0]} barSize={12} />
              <Bar dataKey="invoices" fill="#18b7a4" radius={[2,2,0,0]} barSize={12} />
            </BarChart>
          </ResponsiveContainer>
        </Card>
        <Card className="chart-card">
          <div className="chart-title"><h3>Customer Status Distribution</h3></div>
          <div className="donut-layout">
            <ResponsiveContainer width="100%" height={205}>
              <PieChart><Pie data={data.customer_status} dataKey="value" nameKey="name" cx="50%" cy="50%" innerRadius={52} outerRadius={84} paddingAngle={1}>{data.customer_status.map((_, i) => <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />)}</Pie><Tooltip /></PieChart>
            </ResponsiveContainer>
            <div className="donut-legend">
              {data.customer_status.map((item, i) => <div className="donut-row" key={item.name}><span><i className="legend-dot" style={{background:PIE_COLORS[i]}} />{item.name}</span><b>{item.value}</b></div>)}
            </div>
          </div>
        </Card>
      </div>

      <div className="dashboard-bottom">
        <Card className="compact-panel">
          <div className="card-head"><h3>Pending Payments</h3><button className="link-button" onClick={() => navigate('/invoices')}>View All</button></div>
          <div className="table-wrap"><table className="data-table compact-table"><thead><tr><th>Customer</th><th>Invoice No.</th><th>Due Date</th><th>Balance</th><th>Status</th></tr></thead><tbody>{data.pending_payments.map(p => <tr key={p.invoice_no}><td>{p.customer}</td><td>{p.invoice_no}</td><td>{shortDate(p.due_date)}</td><td className="amount">{currency(p.balance)}</td><td><Status value={p.status} /></td></tr>)}</tbody></table></div>
          <div className="panel-total"><span>Total Outstanding</span><span className="amount danger">{currency(m.pending_payments)}</span></div>
        </Card>
        <Card className="compact-panel">
          <div className="card-head"><h3>Today's Follow-ups</h3><button className="link-button" onClick={() => navigate('/followups')}>View All</button></div>
          <div className="followup-list">{data.today_followups.map((f, i) => <div className="followup-row" key={i}><div className="time-pill">{f.time}</div><div><b>{f.customer}</b><small className="cell-sub">{f.purpose}</small></div><Status value={f.channel} /></div>)}
          {!data.today_followups.length && <div className="muted" style={{ padding: '8px 0' }}>No follow-ups scheduled for today</div>}</div>
        </Card>
        <Card className="compact-panel">
          <div className="card-head"><h3>Recent Activity</h3></div>
          <div className="activity-list">{data.recent_activity.map((a, i) => <div className="activity-item" key={i}><div className="activity-icon">{a.type === 'payment' ? <IndianRupee size={16}/> : <ReceiptText size={16}/>}</div><div className="activity-copy"><b>{a.title}</b><small>{a.detail}</small></div><small>{a.when}</small></div>)}
          {!data.recent_activity.length && <div className="muted" style={{ padding: '8px 0' }}>No recent activity yet</div>}</div>
        </Card>
      </div>
    </>
  );
}
