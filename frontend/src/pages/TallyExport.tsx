import { useState } from 'react';
import { Download } from 'lucide-react';
import { Button, Card, Field, Input, PageHeader } from '../components/UI';

const firstOfMonth = () => { const d = new Date(); d.setDate(1); return d.toISOString().slice(0, 10); };
const today = () => new Date().toISOString().slice(0, 10);

export default function TallyExport() {
  const [fromDate, setFromDate] = useState(firstOfMonth());
  const [toDate, setToDate] = useState(today());

  const downloadMasters = () => {
    const a = document.createElement('a');
    a.href = '/api/tally/export/masters';
    a.download = 'tally-masters.xml';
    a.click();
  };

  const downloadVouchers = () => {
    const a = document.createElement('a');
    a.href = `/api/tally/export/vouchers?from_date=${fromDate}&to_date=${toDate}`;
    a.download = `tally-vouchers-${fromDate}-to-${toDate}.xml`;
    a.click();
  };

  return <>
    <PageHeader title="Tally Export" subtitle="Export ledgers and vouchers as Tally-compatible XML" />
    <Card className="settings-card">
      <h3>1. Ledger Masters</h3>
      <p className="muted" style={{ fontSize: 13.5, lineHeight: 1.6, marginBottom: 12 }}>
        Exports every chart-of-accounts ledger plus one ledger per customer (under Sundry Debtors) and vendor (under Sundry Creditors).
        Import this first in Tally via Gateway of Tally &gt; Import Data &gt; Masters, before importing vouchers.
      </p>
      <Button onClick={downloadMasters}><Download size={15} /> Download Masters XML</Button>
    </Card>

    <Card className="settings-card">
      <h3>2. Vouchers</h3>
      <p className="muted" style={{ fontSize: 13.5, lineHeight: 1.6, marginBottom: 12 }}>
        Exports every journal entry in the selected period as a Tally voucher (Sales, Receipt, Purchase, Payment, Credit/Debit Note, or Journal).
        Import via Gateway of Tally &gt; Import Data &gt; Day Book / Vouchers, after the masters above are already in Tally.
      </p>
      <div className="form-grid">
        <Field label="From Date"><Input type="date" value={fromDate} onChange={e => setFromDate(e.target.value)} /></Field>
        <Field label="To Date"><Input type="date" value={toDate} onChange={e => setToDate(e.target.value)} /></Field>
      </div>
      <div className="form-actions"><Button onClick={downloadVouchers}><Download size={15} /> Download Vouchers XML</Button></div>
    </Card>

    <Card className="settings-card">
      <h3>Before you rely on this</h3>
      <p className="muted" style={{ fontSize: 13.5, lineHeight: 1.6 }}>
        This export follows Tally's documented XML import format, but it has not been tested against a live Tally installation.
        Import a small date range first and check a few vouchers land correctly before importing a full period.
      </p>
    </Card>
  </>;
}
