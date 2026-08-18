import { useEffect, useState } from 'react';
import { Eye, Plus, RefreshCw, Search } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import api from '../api';
import { Button, Card, Loading, PageHeader } from '../components/UI';
import { JournalEntry } from '../types';
import { currency, shortDate } from '../utils';
import Pagination, { usePagination } from '../components/Pagination';

export default function Journal() {
  const [entries, setEntries] = useState<JournalEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const navigate = useNavigate();

  const load = () => { setLoading(true); api.get('/journal').then(r => setEntries(r.data)).finally(() => setLoading(false)); };
  useEffect(load, []);

  const filtered = entries.filter(e => `${e.number} ${e.narration} ${e.source_type}`.toLowerCase().includes(search.toLowerCase()));

  const { pageRows, props: pageProps } = usePagination(filtered);

  return <>
    <PageHeader title="Journal" subtitle="Every posting auto-generated from your sales, purchase and expense activity" action={<Button onClick={() => navigate('/journal/new')}><Plus size={15} /> New Entry</Button>}  toolbar={<><div className="search-box"><Search size={16} /><input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search journal number, narration or source..." /></div><Button tone="secondary" onClick={load}><RefreshCw size={15} /> Refresh</Button></>}/>
        <Card className="list-card">{loading ? <Loading /> : <div className="table-wrap"><table className="data-table"><thead><tr><th>Journal No.</th><th>Date</th><th>Narration</th><th>Source</th><th>Total</th><th>Action</th></tr></thead><tbody>{pageRows.map(entry => <tr key={entry.id}>
      <td className="cell-title">{entry.number}</td>
      <td>{shortDate(entry.entry_date)}</td>
      <td>{entry.narration}</td>
      <td>{entry.source_type}</td>
      <td className="amount"><b>{currency(entry.lines.reduce((s, l) => s + Number(l.debit), 0), 2)}</b></td>
      <td><button className="mini-button" title="View" onClick={() => navigate(`/journal/${entry.id}`)}><Eye size={14} /></button></td>
    </tr>)}
    {!filtered.length && <tr><td colSpan={6} className="muted">No journal entries yet</td></tr>}
    </tbody></table></div>}<Pagination {...pageProps} noun="entries" /></Card>
  </>;
}