import { useState } from 'react';
import { Upload } from 'lucide-react';
import api from '../api';
import { Button, Card, Field, Input, PageHeader } from '../components/UI';
import { currency } from '../utils';

type PreviewRow = { name: string; debit: number; credit: number; match_type: 'customer' | 'vendor' | 'account' | 'unmatched'; match_id: number | string | null; match_name: string | null };

const matchTone: Record<string, string> = { customer: 'blue', vendor: 'teal', account: 'green', unmatched: 'red' };
const matchLabel: Record<string, string> = { customer: 'Customer', vendor: 'Vendor', account: 'Account', unmatched: 'Unmatched' };

export default function OpeningBalances() {
  const [file, setFile] = useState<File | null>(null);
  const [asOf, setAsOf] = useState(new Date().toISOString().slice(0, 10));
  const [preview, setPreview] = useState<PreviewRow[] | null>(null);
  const [selected, setSelected] = useState<boolean[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState<{ applied: number; skipped: number } | null>(null);

  const runPreview = async () => {
    if (!file) return;
    setLoading(true);
    setError('');
    setResult(null);
    try {
      const formData = new FormData();
      formData.append('file', file);
      const { data } = await api.post<PreviewRow[]>('/opening-balances/preview', formData, { headers: { 'Content-Type': 'multipart/form-data' } });
      setPreview(data);
      setSelected(data.map(r => r.match_type !== 'unmatched'));
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Could not read this CSV file');
    } finally {
      setLoading(false);
    }
  };

  const runCommit = async () => {
    if (!preview) return;
    setLoading(true);
    try {
      const rows = preview.filter((_, i) => selected[i]).map(r => ({ ...r }));
      const { data } = await api.post('/opening-balances/commit', { rows, as_of: asOf });
      setResult(data);
      setPreview(null);
      setFile(null);
    } finally {
      setLoading(false);
    }
  };

  const selectedCount = selected.filter(Boolean).length;
  const totalDebit = preview?.reduce((s, r, i) => s + (selected[i] ? r.debit : 0), 0) || 0;
  const totalCredit = preview?.reduce((s, r, i) => s + (selected[i] ? r.credit : 0), 0) || 0;

  return <>
    <PageHeader title="Opening Balances" subtitle="Bring your starting financial position over from Tally or any other software" />
    <Card className="settings-card">
      <p className="muted" style={{ fontSize: 13.5, lineHeight: 1.6, marginBottom: 12 }}>
        Upload a trial balance as CSV with columns <b>name, debit, credit</b> — this is what any accounting software (Tally, Zoho, QuickBooks, Excel) exports.
        Each row is matched against your Customers, Vendors, and Chart of Accounts by name. Customer balances are recorded as an opening invoice so they show up
        correctly everywhere in the app; vendor and account balances post directly to the ledger. Import Customers/Vendors first if a party isn't matching.
      </p>
      {!preview && <>
        <div className="form-grid">
          <Field label="Trial Balance CSV" required><Input type="file" accept=".csv" onChange={e => setFile(e.target.files?.[0] || null)} /></Field>
          <Field label="As Of Date" required><Input type="date" value={asOf} onChange={e => setAsOf(e.target.value)} /></Field>
        </div>
        {error && <p style={{ color: '#e02424', fontSize: 13.5 }}>{error}</p>}
        <div className="form-actions"><Button onClick={runPreview} disabled={!file || loading}><Upload size={15} /> Preview</Button></div>
      </>}
    </Card>

    {result && <Card className="settings-card">
      <h3>Import Complete</h3>
      <div className="summary-line"><span>Applied</span><b style={{ color: '#0caf74' }}>{result.applied}</b></div>
      <div className="summary-line"><span>Skipped (unmatched or unsupported)</span><b>{result.skipped}</b></div>
    </Card>}

    {preview && <Card className="list-card">
      <div className="card-head"><h3>Preview ({selectedCount} of {preview.length} selected)</h3></div>
      <div className="table-wrap"><table className="data-table"><thead><tr><th></th><th>Name</th><th>Debit</th><th>Credit</th><th>Resolved As</th></tr></thead><tbody>{preview.map((row, i) => <tr key={i}>
        <td><input type="checkbox" checked={selected[i]} disabled={row.match_type === 'unmatched'} onChange={e => setSelected(prev => prev.map((v, idx) => idx === i ? e.target.checked : v))} /></td>
        <td>{row.name}</td>
        <td className="amount">{row.debit ? currency(row.debit, 2) : ''}</td>
        <td className="amount">{row.credit ? currency(row.credit, 2) : ''}</td>
        <td><span className={`badge ${matchTone[row.match_type]}`}>{matchLabel[row.match_type]}{row.match_name ? `: ${row.match_name}` : ''}</span></td>
      </tr>)}</tbody>
      <tfoot><tr className="invoice-totals grand"><td colSpan={2}>Selected Total</td><td className="amount">{currency(totalDebit, 2)}</td><td className="amount">{currency(totalCredit, 2)}</td><td /></tr></tfoot>
      </table></div>
      <div className="form-actions"><Button tone="secondary" onClick={() => { setPreview(null); setFile(null); }}>Start Over</Button><Button onClick={runCommit} disabled={loading || !selectedCount}>Import {selectedCount} Selected</Button></div>
    </Card>}
  </>;
}
