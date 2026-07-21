import { FormEvent, useEffect, useState } from 'react';
import { Upload, Trash2 } from 'lucide-react';
import api from '../api';
import { Button, Card, Field, Input, Loading, PageHeader, Select } from '../components/UI';
import { BusinessSettings, PricingRule } from '../types';
import { INDIAN_STATES } from '../utils';

export default function SettingsPage() {
  const [rules, setRules] = useState<PricingRule | null>(null);
  const [business, setBusiness] = useState<BusinessSettings | null>(null);
  const [saved, setSaved] = useState('');
  const [uploading, setUploading] = useState(false);

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
  const uploadLogo = async (file?: File) => {
    if (!file) return;
    setUploading(true);
    try {
      const form = new FormData();
      form.append('file', file);
      const { data } = await api.post('/business-settings/logo', form, { headers: { 'Content-Type': 'multipart/form-data' } });
      setBusiness(data);
      flash('Logo uploaded');
    } finally {
      setUploading(false);
    }
  };
  const removeLogo = async () => {
    const { data } = await api.delete('/business-settings/logo');
    setBusiness(data);
    flash('Logo removed');
  };

  return <>
    <PageHeader title="Settings" subtitle="Business profile, bank details, document terms, taxation and pricing defaults" />
    {saved && <div className="toast">{saved}</div>}
    <div className="settings-grid">
      <Card className="settings-card">
        <h3>Business Profile</h3>
        <form onSubmit={saveBusiness}>
          <div className="form-grid">
            <div className="logo-uploader">
              <div className="logo-preview">{business.logo_path ? <img src={`${business.logo_path}?v=${encodeURIComponent(business.updated_at)}`} alt="Business logo" /> : <span>{business.logo_text || 'CF'}</span>}</div>
              <div className="logo-actions">
                <label className="button secondary"><Upload size={15}/> Upload Logo<input type="file" accept="image/png,image/jpeg,image/webp" hidden disabled={uploading} onChange={e => uploadLogo(e.target.files?.[0])} /></label>
                <Button type="button" tone="secondary" onClick={removeLogo} disabled={!business.logo_path || uploading}><Trash2 size={15}/> Remove</Button>
              </div>
            </div>
            <Field label="Business Name"><Input value={business.company_name} onChange={e => setBusiness({ ...business, company_name: e.target.value })} /></Field>
            <Field label="Tagline"><Input value={business.tagline} onChange={e => setBusiness({ ...business, tagline: e.target.value })} /></Field>
            <Field label="GST Number"><Input value={business.gst_number} onChange={e => setBusiness({ ...business, gst_number: e.target.value })} /></Field>
            <Field label="State"><Select value={business.state} onChange={e => setBusiness({ ...business, state: e.target.value })}><option value="">Select state</option>{INDIAN_STATES.map(s => <option key={s}>{s}</option>)}</Select></Field>
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
