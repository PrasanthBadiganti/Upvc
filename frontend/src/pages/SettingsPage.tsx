import { FormEvent, useEffect, useState } from 'react';
import api from '../api';
import { Button, Card, Field, Input, Loading, PageHeader, Select } from '../components/UI';
import { BusinessSettings, PricingRule } from '../types';

export default function SettingsPage() {
  const [rules, setRules] = useState<PricingRule | null>(null);
  const [business, setBusiness] = useState<BusinessSettings | null>(null);
  const [saved, setSaved] = useState('');

  useEffect(() => {
    Promise.all([api.get('/pricing-rules'), api.get('/business-settings')]).then(([ruleRes, businessRes]) => {
      setRules(ruleRes.data);
      setBusiness(businessRes.data);
    });
  }, []);

  if (!rules || !business) return <Loading />;

  const flash = (message: string) => { setSaved(message); setTimeout(() => setSaved(''), 2200); };
  const saveBusiness = async (e: FormEvent) => {
    e.preventDefault();
    const { data } = await api.put('/business-settings', business);
    setBusiness(data);
    flash('Business profile saved');
  };
  const saveRules = async (e: FormEvent) => {
    e.preventDefault();
    const { data } = await api.put('/pricing-rules', rules);
    setRules(data);
    flash('Pricing defaults saved');
  };

  return <>
    <PageHeader title="Settings" subtitle="Business profile, bank details, document terms, taxation and pricing defaults" />
    {saved && <div className="toast">{saved}</div>}
    <div className="settings-grid">
      <Card className="settings-card">
        <h3>Business Profile</h3>
        <form onSubmit={saveBusiness}>
          <div className="form-grid">
            <Field label="Business Name"><Input value={business.company_name} onChange={e => setBusiness({ ...business, company_name: e.target.value })} /></Field>
            <Field label="Tagline"><Input value={business.tagline} onChange={e => setBusiness({ ...business, tagline: e.target.value })} /></Field>
            <Field label="GST Number"><Input value={business.gst_number} onChange={e => setBusiness({ ...business, gst_number: e.target.value })} /></Field>
            <Field label="Logo Text"><Input maxLength={4} value={business.logo_text} onChange={e => setBusiness({ ...business, logo_text: e.target.value })} /></Field>
            <Field label="Phone"><Input value={business.phone} onChange={e => setBusiness({ ...business, phone: e.target.value })} /></Field>
            <Field label="Email"><Input value={business.email} onChange={e => setBusiness({ ...business, email: e.target.value })} /></Field>
            <Field label="Address"><textarea className="input" value={business.address} onChange={e => setBusiness({ ...business, address: e.target.value })} /></Field>
          </div>
          <h3 style={{ marginTop: 16 }}>Bank Details</h3>
          <div className="form-grid">
            <Field label="Bank Name"><Input value={business.bank_name} onChange={e => setBusiness({ ...business, bank_name: e.target.value })} /></Field>
            <Field label="Account Name"><Input value={business.account_name} onChange={e => setBusiness({ ...business, account_name: e.target.value })} /></Field>
            <Field label="Account Number"><Input value={business.account_number} onChange={e => setBusiness({ ...business, account_number: e.target.value })} /></Field>
            <Field label="IFSC"><Input value={business.ifsc} onChange={e => setBusiness({ ...business, ifsc: e.target.value })} /></Field>
            <Field label="UPI ID"><Input value={business.upi_id} onChange={e => setBusiness({ ...business, upi_id: e.target.value })} /></Field>
          </div>
          <h3 style={{ marginTop: 16 }}>Document Terms</h3>
          <div className="form-grid">
            <Field label="Quotation Terms"><textarea className="input" value={business.quotation_terms} onChange={e => setBusiness({ ...business, quotation_terms: e.target.value })} /></Field>
            <Field label="Invoice Terms"><textarea className="input" value={business.invoice_terms} onChange={e => setBusiness({ ...business, invoice_terms: e.target.value })} /></Field>
            <Field label="Payment Receipt Terms"><textarea className="input" value={business.payment_terms} onChange={e => setBusiness({ ...business, payment_terms: e.target.value })} /></Field>
          </div>
          <div className="form-actions"><Button type="submit">Save Business Profile</Button></div>
        </form>
      </Card>
      <Card className="settings-card">
        <h3>Pricing & Tax Defaults</h3>
        <form onSubmit={saveRules}>
          <div className="form-grid">
            <Field label="GST Rate %"><Input type="number" value={Number(rules.gst_rate)} onChange={e => setRules({ ...rules, gst_rate: Number(e.target.value) })} /></Field>
            <Field label="Tax Type"><Select value={rules.tax_type} onChange={e => setRules({ ...rules, tax_type: e.target.value })}><option>Exclusive</option><option>Inclusive</option></Select></Field>
            <Field label="Minimum Billable SFT"><Input type="number" value={Number(rules.minimum_billable_sft)} onChange={e => setRules({ ...rules, minimum_billable_sft: Number(e.target.value) })} /></Field>
            <Field label="Rounding Rule"><Select value={rules.rounding_rule} onChange={e => setRules({ ...rules, rounding_rule: e.target.value })}><option>Round up</option><option>Nearest whole number</option><option>No rounding</option></Select></Field>
            <Field label="Within City Transport"><Input type="number" value={Number(rules.within_city_transport)} onChange={e => setRules({ ...rules, within_city_transport: Number(e.target.value) })} /></Field>
            <Field label="Beyond City Transport"><Input type="number" value={Number(rules.beyond_city_transport)} onChange={e => setRules({ ...rules, beyond_city_transport: Number(e.target.value) })} /></Field>
          </div>
          <div className="form-actions"><Button type="submit">Save Defaults</Button></div>
        </form>
      </Card>
    </div>
  </>;
}
