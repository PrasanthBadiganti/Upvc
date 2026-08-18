import { useEffect, useState } from 'react';
import { CalendarDays, FileText, RotateCcw } from 'lucide-react';
import { useNavigate, useParams } from 'react-router-dom';
import api from '../api';
import { Button, Card, Loading, PageHeader } from '../components/UI';
import { JournalEntry } from '../types';
import { currency, shortDate } from '../utils';
import { useConfirm } from '../contexts/ConfirmContext';

export default function JournalEntryDetails() {
  const confirm = useConfirm();
  const { id } = useParams();
  const navigate = useNavigate();
  const [entry, setEntry] = useState<JournalEntry | null>(null);
  const [reversing, setReversing] = useState(false);

  const load = () => api.get(`/journal/${id}`).then(r => setEntry(r.data));
  useEffect(() => { load(); }, [id]);
  if (!entry) return <Loading />;

  const totalDebit = entry.lines.reduce((s, l) => s + Number(l.debit), 0);
  const totalCredit = entry.lines.reduce((s, l) => s + Number(l.credit), 0);

  const reverse = async () => {
    if (!(await confirm({ title: 'Reverse journal entry', message: 'This posts an offsetting entry and cannot be undone.', confirmLabel: 'Reverse entry', cancelLabel: 'Keep it', isDangerous: true }))) return;
    setReversing(true);
    try {
      const { data } = await api.post(`/journal/${entry.id}/reverse`);
      navigate(`/journal/${data.id}`);
    } catch (err: any) {
      alert(err?.response?.data?.detail || 'Could not reverse this journal entry');
    } finally {
      setReversing(false);
    }
  };

  return <>
    <PageHeader title="Journal Entry Details" action={entry.source_type === 'Manual' ? <Button tone="secondary" onClick={reverse} disabled={reversing}><RotateCcw size={15} /> Reverse Entry</Button> : undefined} />
    <div className="metric-grid invoice-summary-cards">
      <Card className="invoice-summary-card"><div className="metric-icon blue"><FileText size={18} /></div><div><small>Journal No.</small><strong>{entry.number}</strong></div></Card>
      <Card className="invoice-summary-card"><div className="metric-icon blue"><CalendarDays size={18} /></div><div><small>Date</small><strong>{shortDate(entry.entry_date)}</strong></div></Card>
      <Card className="invoice-summary-card"><div className="metric-icon blue"><FileText size={18} /></div><div><small>Source</small><strong>{entry.source_type}</strong></div></Card>
    </div>
    <Card className="invoice-table-card">
      <div className="card-head"><h3>{entry.narration}</h3></div>
      <div className="table-wrap"><table className="data-table"><thead><tr><th>Account</th><th>Debit</th><th>Credit</th></tr></thead><tbody>{entry.lines.map(line => <tr key={line.id}>
        <td><span className="cell-title" style={{ cursor: 'pointer' }} onClick={() => navigate(`/accounts/${line.account_id}`)}>{line.account.code} - {line.account.name}</span></td>
        <td className="amount">{Number(line.debit) > 0 ? currency(line.debit, 2) : ''}</td>
        <td className="amount">{Number(line.credit) > 0 ? currency(line.credit, 2) : ''}</td>
      </tr>)}
      <tr className="invoice-totals grand"><td>Total</td><td className="amount">{currency(totalDebit, 2)}</td><td className="amount">{currency(totalCredit, 2)}</td></tr>
      </tbody></table></div>
    </Card>
  </>;
}
