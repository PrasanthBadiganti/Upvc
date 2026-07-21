import { useState } from 'react';
import api from '../api';
import { Button, Field, Input, Modal } from './UI';

type PreviewRow = { row: Record<string, string>; status: 'new' | 'duplicate'; matched_id: number | null; matched_name: string | null };

export default function ImportModal({ open, onClose, title, previewUrl, commitUrl, columns, extraHelp, acceptTallyXml, showAsOfDate, onImported }: {
  open: boolean;
  onClose: () => void;
  title: string;
  previewUrl: string;
  commitUrl: string;
  columns: { key: string; label: string }[];
  extraHelp?: string;
  acceptTallyXml?: boolean;
  showAsOfDate?: boolean;
  onImported: (count: number) => void;
}) {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<PreviewRow[] | null>(null);
  const [selected, setSelected] = useState<boolean[]>([]);
  const [asOf, setAsOf] = useState(new Date().toISOString().slice(0, 10));
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const reset = () => { setFile(null); setPreview(null); setSelected([]); setError(''); };
  const close = () => { reset(); onClose(); };

  const runPreview = async () => {
    if (!file) return;
    setLoading(true);
    setError('');
    try {
      const formData = new FormData();
      formData.append('file', file);
      const { data } = await api.post<PreviewRow[]>(previewUrl, formData, { headers: { 'Content-Type': 'multipart/form-data' } });
      setPreview(data);
      setSelected(data.map(r => r.status === 'new'));
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Could not read this file');
    } finally {
      setLoading(false);
    }
  };

  const runCommit = async () => {
    if (!preview) return;
    setLoading(true);
    try {
      const rows = preview.filter((_, i) => selected[i]).map(r => r.row);
      const payload: Record<string, unknown> = { rows };
      if (showAsOfDate) payload.as_of = asOf;
      const { data } = await api.post(commitUrl, payload);
      onImported(data.created);
      close();
    } finally {
      setLoading(false);
    }
  };

  const selectedCount = selected.filter(Boolean).length;

  return <Modal open={open} onClose={close} title={title} width={900}>
    {!preview ? <>
      <Field label={acceptTallyXml ? 'CSV or Tally Ledger Masters XML' : 'CSV File'} required><Input type="file" accept={acceptTallyXml ? '.csv,.xml' : '.csv'} onChange={e => setFile(e.target.files?.[0] || null)} /></Field>
      <p className="muted" style={{ fontSize: 12, marginTop: 8 }}>First row must be a header including a <b>name</b> column. Optional columns: phone, email, address, gst_number, notes{extraHelp ? `, ${extraHelp}` : ''}.{acceptTallyXml && ' A Tally ledger-masters XML export (Sundry Debtors/Creditors) is also accepted — name, GSTIN, phone, address and opening balance are read automatically.'}</p>
      {showAsOfDate && <Field label="Opening Balances As Of"><Input type="date" value={asOf} onChange={e => setAsOf(e.target.value)} /></Field>}
      {error && <p style={{ color: '#e02424', fontSize: 12 }}>{error}</p>}
      <div className="form-actions"><Button type="button" tone="secondary" onClick={close}>Cancel</Button><Button type="button" onClick={runPreview} disabled={!file || loading}>Preview</Button></div>
    </> : <>
      <div className="table-wrap" style={{ maxHeight: 380, overflowY: 'auto' }}><table className="data-table"><thead><tr><th></th>{columns.map(c => <th key={c.key}>{c.label}</th>)}<th>Status</th></tr></thead><tbody>{preview.map((r, i) => <tr key={i}>
        <td><input type="checkbox" checked={selected[i]} onChange={e => setSelected(prev => prev.map((v, idx) => idx === i ? e.target.checked : v))} /></td>
        {columns.map(c => <td key={c.key}>{r.row[c.key]}</td>)}
        <td>{r.status === 'duplicate' ? <span className="badge amber">Duplicate of {r.matched_name}</span> : <span className="badge green">New</span>}</td>
      </tr>)}
      {!preview.length && <tr><td colSpan={columns.length + 2} className="muted">No rows found in this file</td></tr>}
      </tbody></table></div>
      <div className="form-actions"><Button type="button" tone="secondary" onClick={close}>Cancel</Button><Button type="button" onClick={runCommit} disabled={loading || !selectedCount}>Import {selectedCount} Selected</Button></div>
    </>}
  </Modal>;
}
