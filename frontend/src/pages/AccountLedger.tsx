import { useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import api from '../api';
import { Card, Loading, PageHeader } from '../components/UI';
import { ChartOfAccount, LedgerLine } from '../types';
import { currency, shortDate } from '../utils';

export default function AccountLedger() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [account, setAccount] = useState<ChartOfAccount | null>(null);
  const [lines, setLines] = useState<LedgerLine[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    Promise.all([api.get('/accounts'), api.get(`/accounts/${id}/ledger`)]).then(([accounts, ledger]) => {
      setAccount(accounts.data.find((a: ChartOfAccount) => a.id === Number(id)) || null);
      setLines(ledger.data);
    }).finally(() => setLoading(false));
  }, [id]);

  const rows = useMemo(() => {
    let running = 0;
    return lines.map(line => {
      running += Number(line.debit) - Number(line.credit);
      return { ...line, running };
    });
  }, [lines]);

  const totals = useMemo(() => ({
    debit: lines.reduce((s, l) => s + Number(l.debit), 0),
    credit: lines.reduce((s, l) => s + Number(l.credit), 0),
  }), [lines]);

  if (loading) return <Loading />;

  return <>
    <PageHeader title={account ? `${account.code} - ${account.name}` : 'Account Ledger'} subtitle={account ? `${account.account_type} / ${account.account_group}` : 'Ledger'} />
    <Card className="list-card"><div className="table-wrap"><table className="data-table"><thead><tr><th>Date</th><th>Journal No.</th><th>Narration</th><th>Debit</th><th>Credit</th><th>Running Balance</th></tr></thead><tbody>{rows.map(line => <tr key={line.id}>
      <td>{shortDate(line.entry.entry_date)}</td>
      <td className="cell-title" style={{ cursor: 'pointer' }} onClick={() => navigate(`/journal/${line.entry.id}`)}>{line.entry.number}</td>
      <td>{line.entry.narration}</td>
      <td className="amount">{Number(line.debit) > 0 ? currency(line.debit, 2) : ''}</td>
      <td className="amount">{Number(line.credit) > 0 ? currency(line.credit, 2) : ''}</td>
      <td className="amount"><b>{currency(line.running, 2)}</b></td>
    </tr>)}
    {!rows.length && <tr><td colSpan={6} className="muted">No ledger activity for this account</td></tr>}
    </tbody><tfoot><tr className="invoice-totals grand"><td colSpan={3} /><td className="amount">{currency(totals.debit, 2)}</td><td className="amount">{currency(totals.credit, 2)}</td><td /></tr></tfoot></table></div></Card>
  </>;
}
