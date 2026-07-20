import { useEffect, useState } from 'react';
import { Eye } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import api from '../api';
import { Card, Loading, PageHeader } from '../components/UI';
import Status from '../components/Status';
import { ChartOfAccount } from '../types';

export default function ChartOfAccounts() {
  const [accounts, setAccounts] = useState<ChartOfAccount[]>([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => { api.get('/accounts').then(r => setAccounts(r.data)).finally(() => setLoading(false)); }, []);

  const groups = ['Asset', 'Liability', 'Equity', 'Income', 'Expense'];

  return <>
    <PageHeader title="Chart of Accounts" subtitle="Ledger accounts used to post every sale, purchase and expense" />
    <Card className="list-card">{loading ? <Loading /> : <div className="table-wrap"><table className="data-table"><thead><tr><th>Code</th><th>Account</th><th>Type</th><th>Group</th><th>Status</th><th>Action</th></tr></thead><tbody>{groups.flatMap(type => accounts.filter(a => a.account_type === type)).map(account => <tr key={account.id}>
      <td className="cell-title">{account.code}</td>
      <td>{account.name}</td>
      <td>{account.account_type}</td>
      <td>{account.account_group}</td>
      <td><Status value={account.status} /></td>
      <td><button className="mini-button" title="View Ledger" onClick={() => navigate(`/accounts/${account.id}`)}><Eye size={14} /></button></td>
    </tr>)}
    {!accounts.length && <tr><td colSpan={6} className="muted">No accounts found</td></tr>}
    </tbody></table></div>}</Card>
  </>;
}
