import { FormEvent, useEffect, useState } from 'react';
import { Edit3, Landmark, Search } from 'lucide-react';
import api from '../api';
import { Button, Card, Field, Input, Loading, Modal, PageHeader, Select } from '../components/UI';
import Status from '../components/Status';
import { BankAccount } from '../types';
import Pagination, { usePagination } from '../components/Pagination';

type BankAccountForm = Omit<BankAccount, 'id' | 'created_at'>;

const blank: BankAccountForm = {
  name: '',
  bank_name: '',
  account_number: '',
  ifsc: '',
  account_type: 'Current',
  status: 'Active',
  notes: '',
};

export default function BankAccounts() {
  const [accounts, setAccounts] = useState<BankAccount[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [status, setStatus] = useState('');
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<BankAccount | null>(null);
  const [form, setForm] = useState<BankAccountForm>(blank);

  const load = async () => {
    setLoading(true);
    const { data } = await api.get('/bank-accounts', { params: { status } });
    setAccounts(data);
    setLoading(false);
  };

  useEffect(() => { load(); }, [status]);

  const filtered = accounts.filter(a => {
    const q = search.trim().toLowerCase();
    if (!q) return true;
    return a.name.toLowerCase().includes(q) || a.bank_name.toLowerCase().includes(q) || a.account_number.includes(q);
  });

  const showAdd = () => {
    setEditing(null);
    setForm(blank);
    setOpen(true);
  };

  const showEdit = (account: BankAccount) => {
    setEditing(account);
    setForm({
      name: account.name,
      bank_name: account.bank_name,
      account_number: account.account_number,
      ifsc: account.ifsc,
      account_type: account.account_type,
      status: account.status,
      notes: account.notes || '',
    });
    setOpen(true);
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (editing) await api.put(`/bank-accounts/${editing.id}`, form);
    else await api.post('/bank-accounts', form);
    setOpen(false);
    await load();
  };

  const { pageRows, props: pageProps } = usePagination(filtered);

  return <>
    <PageHeader title="Bank Accounts" subtitle="Bank accounts you can link sales and purchase payments to"  toolbar={<><div className="search-box"><Search size={16} /><input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search by name, bank, account number..." /></div>
      <Select value={status} onChange={e => setStatus(e.target.value)} style={{ width: 130 }}><option value="">All Status</option><option>Active</option><option>Inactive</option></Select>
      <Button onClick={showAdd}><Landmark size={16} /> Add Bank Account</Button></>}/>
        <Card className="list-card">{loading ? <Loading /> : <div className="table-wrap"><table className="data-table"><thead><tr><th>Account</th><th>Bank</th><th>Account Number</th><th>IFSC</th><th>Type</th><th>Status</th><th>Action</th></tr></thead><tbody>{pageRows.map(account => <tr key={account.id}>
      <td className="cell-title">{account.name}</td>
      <td>{account.bank_name || '--'}</td>
      <td>{account.account_number || '--'}</td>
      <td>{account.ifsc || '--'}</td>
      <td>{account.account_type}</td>
      <td><Status value={account.status} /></td>
      <td><button className="mini-button" onClick={() => showEdit(account)}><Edit3 size={14} /></button></td>
    </tr>)}
    {!filtered.length && <tr><td colSpan={7} className="muted">No bank accounts found</td></tr>}
    </tbody></table></div>}<Pagination {...pageProps} noun="accounts" /></Card>

    <Modal open={open} onClose={() => setOpen(false)} title={editing ? 'Edit Bank Account' : 'Add Bank Account'} width={640}>
      <form onSubmit={submit}>
        <div className="form-grid">
          <Field label="Account Name" required><Input required value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} placeholder="e.g. HDFC Bank - Current A/c" /></Field>
          <Field label="Bank Name"><Input value={form.bank_name} onChange={e => setForm({ ...form, bank_name: e.target.value })} /></Field>
          <Field label="Account Number"><Input value={form.account_number} onChange={e => setForm({ ...form, account_number: e.target.value })} /></Field>
          <Field label="IFSC"><Input value={form.ifsc} onChange={e => setForm({ ...form, ifsc: e.target.value })} /></Field>
          <Field label="Account Type"><Select value={form.account_type} onChange={e => setForm({ ...form, account_type: e.target.value })}><option>Current</option><option>Savings</option><option>OD/CC</option><option>Cash</option></Select></Field>
          <Field label="Status"><Select value={form.status} onChange={e => setForm({ ...form, status: e.target.value })}><option>Active</option><option>Inactive</option></Select></Field>
          <Field label="Notes"><textarea className="input" value={form.notes} onChange={e => setForm({ ...form, notes: e.target.value })} /></Field>
        </div>
        <div className="form-actions"><Button type="button" tone="secondary" onClick={() => setOpen(false)}>Cancel</Button><Button type="submit"><Landmark size={14} /> {editing ? 'Update' : 'Save'} Bank Account</Button></div>
      </form>
    </Modal>
  </>;
}