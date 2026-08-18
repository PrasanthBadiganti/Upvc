import { useEffect, useState } from 'react';
import { Download } from 'lucide-react';
import api from '../api';
import { Button, Card, CollapsibleSection, Field, Input, Loading, PageHeader } from '../components/UI';
import { currency } from '../utils';

type Gstr1 = {
  b2b: Array<{ gstin: string; customer_name: string; invoice_number: string; invoice_date: string; invoice_value: number; taxable_value: number; rate: number; cgst: number; sgst: number; igst: number }>;
  b2c: Array<{ rate: number; taxable_value: number; cgst: number; sgst: number; igst: number }>;
  cdnr: Array<{ type: string; note_number: string; note_date: string; against_invoice: string; gstin: string; customer_name: string; taxable_value: number; tax_amount: number }>;
  hsn_summary: Array<{ hsn_code: string; description: string; unit: string; quantity: number; taxable_value: number; tax_amount: number; total_value: number }>;
  totals: { b2b_taxable_value: number; b2c_taxable_value: number };
};

type Gstr3b = {
  outward_taxable_supplies: { taxable_value: number; cgst: number; sgst: number; igst: number; total_tax: number };
  eligible_itc: { cgst: number; sgst: number; igst: number; total_itc: number };
  net_tax_payable: { cgst: number; sgst: number; igst: number; total: number };
};

const firstOfMonth = () => { const d = new Date(); d.setDate(1); return d.toISOString().slice(0, 10); };
const today = () => new Date().toISOString().slice(0, 10);

export default function GstReports() {
  const [fromDate, setFromDate] = useState(firstOfMonth());
  const [toDate, setToDate] = useState(today());
  const [gstr1, setGstr1] = useState<Gstr1 | null>(null);
  const [gstr3b, setGstr3b] = useState<Gstr3b | null>(null);
  const [loading, setLoading] = useState(true);

  const load = () => {
    setLoading(true);
    Promise.all([
      api.get('/gst/gstr1', { params: { from_date: fromDate, to_date: toDate } }),
      api.get('/gst/gstr3b', { params: { from_date: fromDate, to_date: toDate } }),
    ]).then(([r1, r3b]) => { setGstr1(r1.data); setGstr3b(r3b.data); }).finally(() => setLoading(false));
  };

  useEffect(load, []);

  const downloadCsv = (path: string, filename: string) => {
    const a = document.createElement('a');
    a.href = `/api/${path}?from_date=${fromDate}&to_date=${toDate}`;
    a.download = filename;
    a.click();
  };

  return <>
    <PageHeader title="GST Reports" subtitle="GSTR-1, GSTR-3B, HSN summary and registers for return filing" />
    <Card className="settings-card">
      <div className="form-grid">
        <Field label="From Date"><Input type="date" value={fromDate} onChange={e => setFromDate(e.target.value)} /></Field>
        <Field label="To Date"><Input type="date" value={toDate} onChange={e => setToDate(e.target.value)} /></Field>
      </div>
      <div className="form-actions">
        <Button onClick={load}>Run Reports</Button>
        <Button tone="secondary" onClick={() => downloadCsv('gst/gstr1/json', `gstr1-${fromDate}-to-${toDate}.json`)}><Download size={14} /> Download GSTR-1 JSON</Button>
      </div>
      <p className="muted" style={{ marginTop: 8, fontSize: 12.5 }}>GSTR-1 JSON is in the GST portal's offline-tool upload format (b2b/b2cs/cdnr/hsn). Validate it against the offline tool before relying on it for a real filing — GSTN updates this schema periodically.</p>
    </Card>

    {loading ? <Loading /> : gstr1 && gstr3b && <>
      <div className="report-grid">
        <Card className="settings-card"><h3>Outward Taxable Supplies (3.1)</h3><div className="summary-line"><span>Taxable Value</span><b>{currency(gstr3b.outward_taxable_supplies.taxable_value, 2)}</b></div><div className="summary-line"><span>CGST</span><b>{currency(gstr3b.outward_taxable_supplies.cgst, 2)}</b></div><div className="summary-line"><span>SGST</span><b>{currency(gstr3b.outward_taxable_supplies.sgst, 2)}</b></div><div className="summary-line"><span>IGST</span><b>{currency(gstr3b.outward_taxable_supplies.igst, 2)}</b></div></Card>
        <Card className="settings-card"><h3>Eligible ITC</h3><div className="summary-line"><span>Input CGST</span><b>{currency(gstr3b.eligible_itc.cgst, 2)}</b></div><div className="summary-line"><span>Input SGST</span><b>{currency(gstr3b.eligible_itc.sgst, 2)}</b></div><div className="summary-line"><span>Input IGST</span><b>{currency(gstr3b.eligible_itc.igst, 2)}</b></div><div className="summary-line"><span>Total ITC</span><b>{currency(gstr3b.eligible_itc.total_itc, 2)}</b></div></Card>
        <Card className="settings-card"><h3>Net Tax Payable</h3><div className="summary-line"><span>CGST Payable</span><b>{currency(gstr3b.net_tax_payable.cgst, 2)}</b></div><div className="summary-line"><span>SGST Payable</span><b>{currency(gstr3b.net_tax_payable.sgst, 2)}</b></div><div className="summary-line"><span>IGST Payable</span><b>{currency(gstr3b.net_tax_payable.igst, 2)}</b></div><div className="summary-line total"><span>Total Payable</span><b>{currency(gstr3b.net_tax_payable.total, 2)}</b></div></Card>
      </div>

      <CollapsibleSection title="B2B Invoices (GSTR-1)" count={gstr1.b2b.length} defaultOpen>
        <div className="table-wrap"><table className="data-table"><thead><tr><th>Invoice No.</th><th>Date</th><th>Customer</th><th>GSTIN</th><th>Taxable Value</th><th>Rate</th><th>CGST</th><th>SGST</th><th>IGST</th><th>Invoice Value</th></tr></thead><tbody>{gstr1.b2b.map(row => <tr key={row.invoice_number}><td className="cell-title">{row.invoice_number}</td><td>{row.invoice_date}</td><td>{row.customer_name}</td><td>{row.gstin}</td><td className="amount">{currency(row.taxable_value, 2)}</td><td>{row.rate}%</td><td className="amount">{currency(row.cgst, 2)}</td><td className="amount">{currency(row.sgst, 2)}</td><td className="amount">{currency(row.igst, 2)}</td><td className="amount"><b>{currency(row.invoice_value, 2)}</b></td></tr>)}
        {!gstr1.b2b.length && <tr><td colSpan={10} className="muted">No B2B invoices in this period</td></tr>}
        </tbody></table></div>
      </CollapsibleSection>

      <CollapsibleSection title="B2C Summary (by rate)" count={gstr1.b2c.length}>
        <div className="table-wrap"><table className="data-table"><thead><tr><th>Rate</th><th>Taxable Value</th><th>CGST</th><th>SGST</th><th>IGST</th></tr></thead><tbody>{gstr1.b2c.map(row => <tr key={row.rate}><td>{row.rate}%</td><td className="amount">{currency(row.taxable_value, 2)}</td><td className="amount">{currency(row.cgst, 2)}</td><td className="amount">{currency(row.sgst, 2)}</td><td className="amount">{currency(row.igst, 2)}</td></tr>)}
        {!gstr1.b2c.length && <tr><td colSpan={5} className="muted">No B2C invoices in this period</td></tr>}
        </tbody></table></div>
      </CollapsibleSection>

      <CollapsibleSection title="Credit / Debit Notes (CDNR)" count={gstr1.cdnr.length}>
        <div className="table-wrap"><table className="data-table"><thead><tr><th>Type</th><th>Note No.</th><th>Date</th><th>Against Invoice</th><th>Customer</th><th>Taxable Value</th><th>Tax</th></tr></thead><tbody>{gstr1.cdnr.map(row => <tr key={row.note_number}><td>{row.type}</td><td className="cell-title">{row.note_number}</td><td>{row.note_date}</td><td>{row.against_invoice}</td><td>{row.customer_name}</td><td className="amount">{currency(row.taxable_value, 2)}</td><td className="amount">{currency(row.tax_amount, 2)}</td></tr>)}
        {!gstr1.cdnr.length && <tr><td colSpan={7} className="muted">No credit/debit notes in this period</td></tr>}
        </tbody></table></div>
      </CollapsibleSection>

      <CollapsibleSection title="HSN Summary (Table 12)" count={gstr1.hsn_summary.length}
        actions={<Button tone="secondary" onClick={() => downloadCsv('gst/hsn-summary/csv', `hsn-summary-${fromDate}-to-${toDate}.csv`)}><Download size={14} /> Download CSV</Button>}>
        <div className="table-wrap"><table className="data-table"><thead><tr><th>HSN Code</th><th>Description</th><th>Unit</th><th>Quantity</th><th>Taxable Value</th><th>Tax Amount</th><th>Total Value</th></tr></thead><tbody>{gstr1.hsn_summary.map(row => <tr key={row.hsn_code}><td className="cell-title">{row.hsn_code}</td><td>{row.description}</td><td>{row.unit}</td><td>{row.quantity}</td><td className="amount">{currency(row.taxable_value, 2)}</td><td className="amount">{currency(row.tax_amount, 2)}</td><td className="amount"><b>{currency(row.total_value, 2)}</b></td></tr>)}
        {!gstr1.hsn_summary.length && <tr><td colSpan={7} className="muted">No HSN activity in this period</td></tr>}
        </tbody></table></div>
      </CollapsibleSection>

      <CollapsibleSection title="Registers">
        <div className="form-actions" style={{ justifyContent: 'flex-start', gap: 12 }}>
          <Button tone="secondary" onClick={() => downloadCsv('gst/sales-register/csv', `sales-register-${fromDate}-to-${toDate}.csv`)}><Download size={14} /> Sales Register CSV</Button>
          <Button tone="secondary" onClick={() => downloadCsv('gst/purchase-register/csv', `purchase-register-${fromDate}-to-${toDate}.csv`)}><Download size={14} /> Purchase Register CSV</Button>
        </div>
      </CollapsibleSection>
    </>}
  </>;
}
