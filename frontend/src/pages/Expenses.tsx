import { FormEvent, useEffect, useState } from 'react';
import { Edit3, Plus, Trash2 } from 'lucide-react';
import api from '../api';
import { Button, Card, Field, Input, Loading, Modal, PageHeader, Select } from '../components/UI';
import { Expense, Vendor } from '../types';
import { currency, shortDate } from '../utils';
import { useConfirm } from '../contexts/ConfirmContext';
import Pagination, { usePagination } from '../components/Pagination';

type ExpenseForm = {
  expense_date: string;
  category: string;
  description: string;
  amount: number;
  gst_percent: number;
  vendor_id: number | null;
  mode: string;
  reference_number: string;
  notes: string;
};

const categories = ['Rent', 'Salaries', 'Utilities', 'Transport', 'Office Supplies', 'Marketing', 'Professional Fees', 'Other'];

const blank: ExpenseForm = {
  expense_date: new Date().toISOString().slice(0, 10),
  category: 'Other',
  description: '',
  amount: 0,
  gst_percent: 0,
  vendor_id: null,
  mode: 'Cash',
  reference_number: '',
  notes: '',
};

export default function Expenses() {
  const confirm = useConfirm();
  const [expenses, setExpenses] = useState<Expense[]>([]);
  const [vendors, setVendors] = useState<Vendor[]>([]);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<Expense | null>(null);
  const [form, setForm] = useState<ExpenseForm>(blank);

  const load = () => { setLoading(true); api.get('/expenses').then(r => setExpenses(r.data)).finally(() => setLoading(false)); };
  useEffect(() => { load(); api.get('/vendors').then(r => setVendors(r.data)); }, []);

  const showAdd = () => { setEditing(null); setForm(blank); setOpen(true); };
  const showEdit = (expense: Expense) => {
    setEditing(expense);
    setForm({
      expense_date: expense.expense_date,
      category: expense.category,
      description: expense.description,
      amount: Number(expense.amount),
      gst_percent: Number(expense.gst_percent),
      vendor_id: expense.vendor_id ?? null,
      mode: expense.mode,
      reference_number: expense.reference_number,
      notes: expense.notes,
    });
    setOpen(true);
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (editing) await api.put(`/expenses/${editing.id}`, form);
    else await api.post('/expenses', form);
    setOpen(false);
    await load();
  };

  const remove = async (expense: Expense) => {
    if (!(await confirm({ title: 'Delete expense', message: `Permanently delete this ${expense.category} expense of ${currency(expense.total, 2)}? Its ledger entries are removed too.`, confirmLabel: 'Delete', cancelLabel: 'Keep it', isDangerous: true }))) return;
    await api.delete(`/expenses/${expense.id}`);
    await load();
  };

  const { pageRows, props: pageProps } = usePagination(expenses);

  return <>
    <PageHeader title="Expenses" subtitle="Day-to-day business outflows" action={<Button onClick={showAdd}><Plus size={15} /> Add Expense</Button>} />
    <Card className="list-card">{loading ? <Loading /> : <div className="table-wrap"><table className="data-table"><thead><tr><th>Date</th><th>Category</th><th>Description</th><th>Vendor</th><th>Mode</th><th>Amount</th><th>GST</th><th>Total</th><th>Action</th></tr></thead><tbody>{pageRows.map(expense => <tr key={expense.id}>
      <td>{shortDate(expense.expense_date)}</td>
      <td>{expense.category}</td>
      <td>{expense.description || '--'}</td>
      <td>{expense.vendor?.name || '--'}</td>
      <td>{expense.mode}</td>
      <td className="amount">{currency(expense.amount, 2)}</td>
      <td className="amount">{currency(expense.gst_amount, 2)}</td>
      <td className="amount"><b>{currency(expense.total, 2)}</b></td>
      <td><div className="action-group"><button className="mini-button" onClick={() => showEdit(expense)}><Edit3 size={14} /></button><button className="mini-button" onClick={() => remove(expense)}><Trash2 size={14} /></button></div></td>
    </tr>)}
    {!expenses.length && <tr><td colSpan={9} className="muted">No expenses recorded</td></tr>}
    </tbody></table></div>}<Pagination {...pageProps} noun="expenses" /></Card>

    <Modal open={open} onClose={() => setOpen(false)} title={editing ? 'Edit Expense' : 'Add Expense'} width={640}>
      <form onSubmit={submit}>
        <div className="form-grid">
          <Field label="Date" required><Input type="date" required value={form.expense_date} onChange={e => setForm({ ...form, expense_date: e.target.value })} /></Field>
          <Field label="Category"><Select value={form.category} onChange={e => setForm({ ...form, category: e.target.value })}>{categories.map(c => <option key={c}>{c}</option>)}</Select></Field>
          <Field label="Description"><Input value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} /></Field>
          <Field label="Amount" required><Input type="number" step="0.01" required value={form.amount} onChange={e => setForm({ ...form, amount: Number(e.target.value) })} /></Field>
          <Field label="GST %"><Input type="number" step="0.01" value={form.gst_percent} onChange={e => setForm({ ...form, gst_percent: Number(e.target.value) })} /></Field>
          <Field label="Vendor (optional)"><Select value={form.vendor_id ?? ''} onChange={e => setForm({ ...form, vendor_id: e.target.value ? Number(e.target.value) : null })}><option value="">None</option>{vendors.map(v => <option key={v.id} value={v.id}>{v.name}</option>)}</Select></Field>
          <Field label="Paid Via"><Select value={form.mode} onChange={e => setForm({ ...form, mode: e.target.value })}><option>Cash</option><option>NEFT</option><option>UPI</option><option>Cheque</option><option>Card</option></Select></Field>
          <Field label="Reference Number"><Input value={form.reference_number} onChange={e => setForm({ ...form, reference_number: e.target.value })} /></Field>
          <Field label="Notes"><Input value={form.notes} onChange={e => setForm({ ...form, notes: e.target.value })} /></Field>
        </div>
        <div className="form-actions"><Button type="button" tone="secondary" onClick={() => setOpen(false)}>Cancel</Button><Button type="submit">{editing ? 'Update' : 'Save'} Expense</Button></div>
      </form>
    </Modal>
  </>;
}