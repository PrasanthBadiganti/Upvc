import { useEffect, useState } from 'react';
import { DatabaseBackup, HardDrive, RefreshCw, RotateCcw, Trash2 } from 'lucide-react';
import api from '../api';
import { Button, Card, Loading, PageHeader } from '../components/UI';
import { useConfirm } from '../contexts/ConfirmContext';
import { shortDate, shortTime } from '../utils';

type BackupFile = { filename: string; timestamp: string; size_mb: number; created: string };
type DbInfo = { path?: string; size_mb?: number; tables?: number; [k: string]: unknown };

export default function Backup() {
  const confirm = useConfirm();
  const [files, setFiles] = useState<BackupFile[]>([]);
  const [info, setInfo] = useState<DbInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState('');
  const [notice, setNotice] = useState('');

  const load = () => {
    setLoading(true);
    Promise.all([api.get('/backup/list'), api.get('/backup/database-info')])
      .then(([l, i]) => { setFiles(l.data.backups ?? []); setInfo(i.data); })
      .finally(() => setLoading(false));
  };
  useEffect(load, []);

  const create = async () => {
    setBusy('create'); setNotice('');
    try {
      const { data } = await api.post('/backup/create');
      setNotice(`Backup created: ${data.filename} (${data.size_mb} MB)`);
      load();
    } catch (e: any) {
      setNotice(e?.response?.data?.detail || 'Could not create the backup');
    } finally { setBusy(''); }
  };

  const restore = async (file: BackupFile) => {
    const okToGo = await confirm({
      title: `Restore ${file.filename}?`,
      message: 'Every change made since this backup was taken will be replaced. A safety copy of the '
        + 'current database is saved first, and UPVC Pro must be closed and reopened afterwards.',
      confirmLabel: 'Restore this backup',
      cancelLabel: 'Keep current data',
      isDangerous: true,
    });
    if (!okToGo) return;
    setBusy(file.filename); setNotice('');
    try {
      const { data } = await api.post(`/backup/restore/${file.filename}`);
      setNotice(`${data.message} Safety copy: ${data.safety_backup}`);
      load();
    } catch (e: any) {
      setNotice(e?.response?.data?.detail || 'Restore failed');
    } finally { setBusy(''); }
  };

  const remove = async (file: BackupFile) => {
    if (!(await confirm({
      title: `Delete ${file.filename}?`,
      message: 'This backup file is removed from disk. It cannot be undone.',
      confirmLabel: 'Delete backup', cancelLabel: 'Keep it', isDangerous: true,
    }))) return;
    setBusy(file.filename);
    try { await api.delete(`/backup/delete/${file.filename}`); load(); }
    finally { setBusy(''); }
  };

  const when = (iso: string) => `${shortDate(iso)} ${shortTime(iso)}`;

  return <>
    <PageHeader title="Backup &amp; Restore" action={<div className="action-group detail-actions">
      <Button onClick={create} disabled={busy === 'create'}><DatabaseBackup size={15} /> {busy === 'create' ? 'Backing up...' : 'Back Up Now'}</Button>
      <Button tone="secondary" onClick={load}><RefreshCw size={15} /> Refresh</Button>
    </div>} toolbar={<span className="muted" style={{ fontSize: 12.5 }}>
      {info?.size_mb !== undefined ? `Current database: ${info.size_mb} MB` : ''}
    </span>} />

    {notice && <div className="toast" style={{ position: 'static', marginBottom: 10 }}>{notice}</div>}

    <Card className="settings-card">
      <div className="summary-line"><span><HardDrive size={14} style={{ verticalAlign: 'middle', marginRight: 6 }} />Database file</span><b style={{ wordBreak: 'break-all' }}>{String(info?.path ?? '--')}</b></div>
      <p className="muted" style={{ margin: '8px 0 0', fontSize: 12.5 }}>
        A backup is taken automatically on a schedule. Restoring replaces the live database and
        writes a safety copy first, so a restore can itself be undone.
      </p>
    </Card>

    <Card className="list-card">
      {loading ? <Loading /> : <div className="table-wrap"><table className="data-table">
        <thead><tr><th>Backup File</th><th>Taken</th><th>Size</th><th>Actions</th></tr></thead>
        <tbody>
          {files.map(f => <tr key={f.filename}>
            <td className="cell-title">{f.filename}</td>
            <td className="nowrap">{when(f.created)}</td>
            <td className="amount">{f.size_mb} MB</td>
            <td><div className="action-group">
              <button className="mini-button" title="Restore this backup" disabled={!!busy} onClick={() => restore(f)}><RotateCcw size={14} /></button>
              <button className="mini-button" title="Delete this backup" disabled={!!busy} onClick={() => remove(f)}><Trash2 size={14} /></button>
            </div></td>
          </tr>)}
          {!files.length && <tr><td colSpan={4} className="muted">No backups yet. Use "Back Up Now" to create the first one.</td></tr>}
        </tbody>
      </table></div>}
    </Card>
  </>;
}
