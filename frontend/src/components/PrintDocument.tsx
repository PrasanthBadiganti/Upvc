// The A4 quotation / invoice document, rendered as ordinary HTML.
//
// Same markup and CSS as quotation_template_final_a4.html, so what prints IS
// the template - no server render, no PDF library. See lib/print.ts.

import { ReactNode } from 'react';
import { createPortal } from 'react-dom';

import { BusinessSettings, Invoice, Quotation } from '../types';

// The print stylesheet hides #root so only this document reaches the paper,
// so it has to live OUTSIDE #root - hence the portal to document.body.
const Portal = ({ children }: { children: ReactNode }) =>
  createPortal(<div className="print-portal">{children}</div>, document.body);

const inr = (value: number | string | undefined, decimals = 2) => {
  const n = Number(value || 0);
  const sign = n < 0 ? '-' : '';
  const [whole, frac] = Math.abs(n).toFixed(decimals).split('.');
  let head = whole;
  let out: string;
  if (head.length > 3) {
    out = head.slice(-3);
    head = head.slice(0, -3);
    while (head.length > 2) { out = `${head.slice(-2)},${out}`; head = head.slice(0, -2); }
    if (head) out = `${head},${out}`;
  } else { out = head; }
  return `${sign}₹${out}${frac ? `.${frac}` : ''}`;
};

const num = (value: number | string | undefined, decimals = 2) =>
  Number(value || 0).toLocaleString('en-IN', {
    minimumFractionDigits: decimals, maximumFractionDigits: decimals,
  });

const day = (iso: string) => {
  const d = new Date(`${iso}T00:00:00`);
  return `${String(d.getDate()).padStart(2, '0')}-${d.toLocaleString('en-GB', { month: 'short' })}-${d.getFullYear()}`;
};

const DOT = ' · ';

type Row = { label: string; value: string; kind?: 'discount' | 'total' };

function Letterhead({ business }: { business: BusinessSettings }) {
  const lines = [
    ...(business.address || '').split('\n').map(s => s.trim()).filter(Boolean),
    business.phone ? `Phone: ${business.phone}` : '',
    business.email ? `Email: ${business.email}` : '',
    business.gst_number ? `GST: ${business.gst_number}` : '',
  ].filter(Boolean);
  return (
    <div className="doc-header">
      {business.logo_path
        ? <div className="doc-logo has-logo"><img src={business.logo_path} alt="" /></div>
        : <div className="doc-logo">{business.logo_text || 'COMPANY LOGO'}</div>}
      <div className="doc-company">
        <div className="doc-company-name">{business.company_name}</div>
        <div className="doc-company-details">
          {lines.map((l, i) => <div key={i}>{l}</div>)}
        </div>
      </div>
    </div>
  );
}

function Cards({ billTo, label, details }: {
  billTo: string[]; label: string; details: [string, string][];
}) {
  return (
    <div className="doc-cards">
      <div className="doc-card">
        <div className="doc-card-label">BILL TO:</div>
        <div className="doc-card-value">
          {billTo.map((l, i) => <div key={i}>{i === 0 ? <strong>{l}</strong> : l}</div>)}
        </div>
      </div>
      <div className="doc-card">
        <div className="doc-card-label">{label}</div>
        <div className="doc-card-value">
          {details.map(([k, v]) => (
            <div className="doc-detail-row" key={k}><span>{k}</span><span>{v}</span></div>
          ))}
        </div>
      </div>
    </div>
  );
}

function Summary({ rows }: { rows: Row[] }) {
  return (
    <div className="doc-summary">
      {rows.map((r, i) => (
        <div key={i} className={`doc-summary-row${r.kind ? ` doc-${r.kind}` : ''}`}>
          <span>{r.label}</span><span>{r.value}</span>
        </div>
      ))}
    </div>
  );
}

function ItemsHead() {
  return (
    <thead><tr>
      <th className="c-num">S.No</th><th>Description</th><th className="c-hsn">HSN</th>
      <th className="c-qty">Qty</th><th className="c-unit">Unit</th>
      <th className="c-rate">Rate</th><th className="c-amt">Amount</th>
    </tr></thead>
  );
}

const taxRows = (cgst: number, sgst: number, igst: number, taxable: number): Row[] => {
  const pct = (part: number) =>
    (taxable > 0 ? ` (${(part / taxable * 100).toFixed(2).replace(/\.?0+$/, '')}%)` : '');
  if (igst > 0) return [{ label: `IGST${pct(igst)}:`, value: inr(igst) }];
  return [
    { label: `CGST${pct(cgst)}:`, value: inr(cgst) },
    { label: `SGST${pct(sgst)}:`, value: inr(sgst) },
  ];
};

export function QuotationPrintDoc({ quotation: q, business }: {
  quotation: Quotation; business: BusinessSettings;
}) {
  const charges = q.charges ?? [];
  const subtotal = Number(q.subtotal || 0);
  const transport = Number(q.transport || 0);
  const discount = Number(q.discount || 0);
  const gst = Number(q.gst || 0);
  const taxableCharges = charges.filter(c => c.taxable).reduce((s, c) => s + Number(c.amount || 0), 0);
  const taxable = subtotal + transport + taxableCharges - discount;

  const rows: Row[] = [{ label: 'Subtotal:', value: inr(subtotal) }];
  if (transport > 0) rows.push({ label: 'Transport:', value: inr(transport) });
  charges.filter(c => c.taxable).forEach(c => rows.push({ label: `${c.label}:`, value: inr(c.amount) }));
  if (discount > 0) rows.push({ label: 'Discount:', value: `-${inr(discount)}`, kind: 'discount' });
  if (taxable !== subtotal) rows.push({ label: 'Taxable Value:', value: inr(taxable) });

  const cs = (q.customer.state || '').trim().toLowerCase();
  const bs = (business.state || '').trim().toLowerCase();
  const half = Math.round(gst / 2 * 100) / 100;
  rows.push(...(cs && bs && cs !== bs
    ? taxRows(0, 0, gst, taxable)
    : taxRows(half, gst - half, 0, taxable)));
  charges.filter(c => !c.taxable)
    .forEach(c => rows.push({ label: `${c.label} (no GST):`, value: inr(c.amount) }));
  rows.push({ label: 'GRAND TOTAL:', value: inr(q.grand_total), kind: 'total' });

  const valid = new Date(`${q.quotation_date}T00:00:00`);
  valid.setDate(valid.getDate() + (q.validity_days || 0));

  const billTo = [q.customer.name,
    ...((q.address || q.customer.address || '').split('\n').map(s => s.trim()).filter(Boolean)),
    q.customer.phone ? `Phone: ${q.customer.phone}` : '',
    q.customer.gst_number ? `GST: ${q.customer.gst_number}` : ''].filter(Boolean);

  return (
    <Portal>
      <div className="a4-doc">
        <Letterhead business={business} />
        <div className="doc-title">QUOTATION</div>
        <Cards billTo={billTo} label="QUOTATION DETAILS" details={[
          ['Ref No:', q.number], ['Date:', day(q.quotation_date)],
          ['Valid Till:', day(valid.toISOString().slice(0, 10))],
        ]} />
        <table className="doc-table">
          <ItemsHead />
          <tbody>
            {q.items.map((it, i) => (
              <tr key={it.id ?? i}>
                <td className="c-num">{i + 1}</td>
                <td>
                  {[it.category, it.style].filter(Boolean).join(' ')}
                  <div className="doc-item-sub">
                    {[Number(it.width_mm) && Number(it.height_mm)
                      ? `${num(it.width_mm, 0)} x ${num(it.height_mm, 0)} mm` : '',
                      it.quantity ? `${it.quantity} nos` : '', it.location]
                      .filter(Boolean).join(DOT)}
                  </div>
                </td>
                <td>{it.hsn_code || '-'}</td>
                <td className="c-qty">{num(it.total_sft)}</td>
                <td>Sq. Ft.</td>
                <td className="c-rate">{inr(it.rate_per_sft)}</td>
                <td className="c-amt">{inr(it.amount)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <Summary rows={rows} />
        {(q.quotation_terms || business.quotation_terms) && (
          <div className="doc-footer">
            <strong>Terms &amp; Conditions:</strong> {q.quotation_terms || business.quotation_terms}
          </div>
        )}
      </div>
    </Portal>
  );
}

export function InvoicePrintDoc({ invoice: inv, business }: {
  invoice: Invoice; business: BusinessSettings;
}) {
  const charges = inv.charges ?? [];
  const subtotal = Number(inv.subtotal || 0);
  const transport = Number(inv.transport || 0);
  const discount = Number(inv.discount || 0);
  const taxableCharges = charges.filter(c => c.taxable).reduce((s, c) => s + Number(c.amount || 0), 0);
  const taxable = subtotal + transport + taxableCharges - discount;

  const rows: Row[] = [{ label: 'Subtotal:', value: inr(subtotal) }];
  if (transport > 0) rows.push({ label: 'Transport:', value: inr(transport) });
  charges.filter(c => c.taxable).forEach(c => rows.push({ label: `${c.label}:`, value: inr(c.amount) }));
  if (discount > 0) rows.push({ label: 'Discount:', value: `-${inr(discount)}`, kind: 'discount' });
  if (taxable !== subtotal) rows.push({ label: 'Taxable Value:', value: inr(taxable) });
  rows.push(...taxRows(Number(inv.cgst || 0), Number(inv.sgst || 0), Number(inv.igst || 0), taxable));
  charges.filter(c => !c.taxable)
    .forEach(c => rows.push({ label: `${c.label} (no GST):`, value: inr(c.amount) }));
  rows.push({ label: 'GRAND TOTAL:', value: inr(inv.grand_total), kind: 'total' });
  if (Number(inv.paid_amount || 0) > 0) {
    rows.push({ label: 'Amount Paid:', value: inr(inv.paid_amount) });
    rows.push({ label: 'Balance Due:', value: inr(inv.pending_balance) });
  }

  const billTo = [inv.customer.name,
    ...((inv.customer.address || '').split('\n').map(s => s.trim()).filter(Boolean)),
    inv.customer.phone ? `Phone: ${inv.customer.phone}` : '',
    inv.customer.gst_number ? `GST: ${inv.customer.gst_number}` : ''].filter(Boolean);

  const bank = ([
    ['Bank:', business.bank_name], ['Account Name:', business.account_name],
    ['Account No.:', business.account_number], ['IFSC:', business.ifsc],
    ['UPI:', business.upi_id],
  ] as [string, string][]).filter(([, v]) => !!v);

  return (
    <Portal>
      <div className="a4-doc">
        <Letterhead business={business} />
        <div className="doc-title">TAX INVOICE</div>
        <Cards billTo={billTo} label="INVOICE DETAILS" details={[
          ['Invoice No:', inv.number], ['Date:', day(inv.invoice_date)],
          ['Due Date:', day(inv.due_date)], ['Status:', inv.status],
        ]} />
        <table className="doc-table">
          <ItemsHead />
          <tbody>
            {inv.items.map((it, i) => (
              <tr key={it.id ?? i}>
                <td className="c-num">{i + 1}</td>
                <td>{it.description}</td>
                <td>{it.hsn_code || '-'}</td>
                <td className="c-qty">{num(it.quantity)}</td>
                <td>{it.unit || 'Nos'}</td>
                <td className="c-rate">{inr(it.rate)}</td>
                <td className="c-amt">{inr(it.amount)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <Summary rows={rows} />
        {business.invoice_terms && (
          <div className="doc-footer">
            <strong>Terms &amp; Conditions:</strong> {business.invoice_terms}
          </div>
        )}
        {bank.length > 0 && (
          <div className="doc-bank-row">
            <div className="doc-card">
              <div className="doc-card-label">BANK / PAYMENT DETAILS</div>
              <div className="doc-card-value">
                {bank.map(([k, v]) => (
                  <div className="doc-detail-row" key={k}><span>{k}</span><span>{v}</span></div>
                ))}
              </div>
            </div>
            <div className="doc-sign">
              <div>For {business.company_name}</div>
              <div className="doc-sign-line">Authorised Signatory</div>
            </div>
          </div>
        )}
      </div>
    </Portal>
  );
}
