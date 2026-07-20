import { FormEvent, useEffect, useMemo, useState } from 'react';
import { Edit3, PackagePlus, Percent, Search, Settings2, Tag, Truck, Wrench } from 'lucide-react';
import api from '../api';
import { Button, Card, Field, Input, Loading, Modal, PageHeader, Select } from '../components/UI';
import Status from '../components/Status';
import { CatalogItem, PricingRule } from '../types';
import { currency, shortDate, shortTime } from '../utils';

type CatalogForm = Omit<CatalogItem, 'id' | 'updated_at'>;

const blankItem: CatalogForm = {
  category: 'Windows',
  product_type: 'Sliding',
  name: '',
  subtitle: '',
  profile_brand: 'VEKA',
  profile_series: 'Euroline 60 mm',
  profile: 'VEKA 60 mm',
  track: '2 Track',
  glass_type: 'Clear Toughened',
  glass_thickness: '5 mm',
  glass_color: 'Clear',
  glass: '5 MM Saint Gobain',
  hardware: 'McCoy Hardware',
  reinforcement: '1.5 mm GI',
  mesh: 'SS Mesh',
  color: 'White',
  hsn_code: '',
  min_billable_sft: 5,
  rate_per_sft: 0,
  gst_percent: 18,
  installation_rate: 120,
  rounding_rule: 'Round up',
  status: 'Active',
};

const productCategories = ['Windows', 'Doors', 'Glass', 'Mesh', 'Partitions', 'Custom'];
const productTypes = ['Sliding', 'Casement', 'Fixed', 'French', 'Openable', 'Partition', 'Custom'];
const roundingRules = ['Round up', 'Nearest whole number', 'No rounding'];

export default function Catalog() {
  const [items, setItems] = useState<CatalogItem[]>([]);
  const [rules, setRules] = useState<PricingRule | null>(null);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState('');
  const [productType, setProductType] = useState('');
  const [status, setStatus] = useState('');
  const [tab, setTab] = useState('Products');
  const [itemOpen, setItemOpen] = useState(false);
  const [rulesOpen, setRulesOpen] = useState(false);
  const [editing, setEditing] = useState<CatalogItem | null>(null);
  const [form, setForm] = useState<CatalogForm>(blankItem);

  const load = async () => {
    setLoading(true);
    const [catalog, pricing] = await Promise.all([
      api.get('/catalog', { params: { search, category, product_type: productType, status } }),
      api.get('/pricing-rules'),
    ]);
    setItems(catalog.data);
    setRules(pricing.data);
    setLoading(false);
  };

  useEffect(() => { load(); }, [search, category, productType, status]);

  const summary = useMemo(() => ({
    active: items.filter(item => item.status === 'Active').length,
    categories: Array.from(new Set(items.map(item => item.category))).length,
    avgRate: items.length ? items.reduce((sum, item) => sum + Number(item.rate_per_sft || 0), 0) / items.length : 0,
  }), [items]);

  const showAdd = () => {
    setEditing(null);
    setForm(blankItem);
    setItemOpen(true);
  };

  const showEdit = (item: CatalogItem) => {
    setEditing(item);
    setForm({
      category: item.category,
      product_type: item.product_type,
      name: item.name,
      subtitle: item.subtitle,
      profile_brand: item.profile_brand || '',
      profile_series: item.profile_series || '',
      profile: item.profile,
      track: item.track,
      glass_type: item.glass_type || '',
      glass_thickness: item.glass_thickness || '',
      glass_color: item.glass_color || '',
      glass: item.glass,
      hardware: item.hardware,
      reinforcement: item.reinforcement || '',
      mesh: item.mesh || '',
      color: item.color,
      hsn_code: item.hsn_code || '',
      min_billable_sft: Number(item.min_billable_sft),
      rate_per_sft: Number(item.rate_per_sft),
      gst_percent: Number(item.gst_percent || 18),
      installation_rate: Number(item.installation_rate || 0),
      rounding_rule: item.rounding_rule || 'Round up',
      status: item.status,
    });
    setItemOpen(true);
  };

  const saveItem = async (event: FormEvent) => {
    event.preventDefault();
    if (editing) await api.put(`/catalog/${editing.id}`, form);
    else await api.post('/catalog', form);
    setItemOpen(false);
    await load();
  };

  const saveRules = async (event: FormEvent) => {
    event.preventDefault();
    if (!rules) return;
    await api.put('/pricing-rules', rules);
    setRulesOpen(false);
    await load();
  };

  return <>
    <PageHeader title="Catalog & Price Master" subtitle="Manage UPVC products, materials and pricing" />
    <div className="catalog-layout">
      <Card className="catalog-main">
        <div className="tabs">{['Products', 'Materials', 'Rates', 'Rules'].map(name => <button key={name} className={`tab ${tab === name ? 'active' : ''}`} onClick={() => setTab(name)}>{name}</button>)}</div>
        <div className="catalog-filters">
          <Field label="Category"><Select value={category} onChange={e => setCategory(e.target.value)}><option value="">All Categories</option>{productCategories.map(item => <option key={item}>{item}</option>)}</Select></Field>
          <Field label="Product Type"><Select value={productType} onChange={e => setProductType(e.target.value)}><option value="">All Types</option>{productTypes.map(item => <option key={item}>{item}</option>)}</Select></Field>
          <Field label="Status"><Select value={status} onChange={e => setStatus(e.target.value)}><option value="">All Status</option><option>Active</option><option>Inactive</option></Select></Field>
          <div className="search-box"><Search size={16} /><input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search product, profile, glass, hardware..." /></div>
          <Button onClick={showAdd}><PackagePlus size={16} /> Add Item</Button>
        </div>

        {loading ? <Loading /> : <div className="table-wrap"><table className="data-table"><thead><tr><th>Product</th><th>Profile</th><th>Glass</th><th>Hardware</th><th>Reinforcement / Mesh</th><th>Color</th><th>HSN</th><th>Billing Rule</th><th>Rate / SFT</th><th>GST</th><th>Status</th><th>Action</th></tr></thead><tbody>{items.map(item => <tr key={item.id}>
          <td><div className="product-cell"><div className="product-image"><i /><i /><i /></div><div><span className="cell-title">{item.name}</span><span className="cell-sub">{item.category} / {item.product_type}</span><span className="cell-sub">{item.subtitle}</span></div></div></td>
          <td><span className="material-chip">{item.profile_brand || item.profile}</span><span className="cell-sub">{item.profile_series || item.profile}</span></td>
          <td><span className="material-chip green">{item.glass_type || item.glass}</span><span className="cell-sub">{item.glass_thickness} {item.glass_color}</span></td>
          <td><span className="material-chip purple">{item.hardware}</span></td>
          <td><span className="cell-title">{item.reinforcement || '--'}</span><span className="cell-sub">{item.mesh || '--'}</span></td>
          <td>{item.color}</td>
          <td>{item.hsn_code || '--'}</td>
          <td>{item.min_billable_sft} SFT<span className="cell-sub">{item.rounding_rule}</span></td>
          <td className="amount success"><b>{currency(item.rate_per_sft)}</b><span className="cell-sub">Install {currency(item.installation_rate)}</span></td>
          <td>{item.gst_percent}%</td>
          <td><Status value={item.status} /></td>
          <td><button className="mini-button" onClick={() => showEdit(item)}><Edit3 size={14} /></button></td>
        </tr>)}
        {!items.length && <tr><td colSpan={12} className="muted">No catalog items found</td></tr>}
        </tbody></table></div>}

        <div className="pagination"><span>{items.length} items | {summary.active} active | {summary.categories} categories | Avg rate {currency(summary.avgRate)}</span><div className="pagination-controls"><button className="page-chip active">1</button><Select style={{ width: 95 }}><option>20 / page</option></Select></div></div>
      </Card>

      <Card className="pricing-panel"><h3>Pricing Rules & Defaults</h3>{rules && <>
        <div className="rule-section"><div className="rule-title"><span><Truck size={15} /></span><div><b>Transport Charges</b><small>Applies to all deliveries</small></div></div><div className="rule-line"><span>Within City</span><b>{currency(rules.within_city_transport)}</b></div><div className="rule-line"><span>Beyond City</span><b>{currency(rules.beyond_city_transport)}</b></div></div>
        <div className="rule-section"><div className="rule-title"><span style={{ background: '#e9faf3', color: '#0caf74' }}><Settings2 size={15} /></span><div><b>Minimum Square Feet</b><small>Default fallback rule</small></div></div><div className="rule-line"><span>Minimum Billable</span><b>{rules.minimum_billable_sft} SFT</b></div><div className="rule-line"><span>Rounding</span><b>{rules.rounding_rule}</b></div></div>
        <div className="rule-section"><div className="rule-title"><span style={{ background: '#f3efff', color: '#7c3aed' }}><Percent size={15} /></span><div><b>GST (Tax)</b></div></div><div className="rule-line"><span>GST Rate</span><b>{rules.gst_rate}%</b></div><div className="rule-line"><span>Type</span><b>{rules.tax_type}</b></div></div>
        <div className="rule-section"><div className="rule-title"><span style={{ background: '#fff5e6', color: '#e99708' }}><Wrench size={15} /></span><div><b>Installation Charges</b></div></div><div className="rule-line"><span>Standard Installation</span><b>{currency(rules.installation_standard)} / SFT</b></div><div className="rule-line"><span>Above 200 SFT</span><b>{currency(rules.installation_above_200)} / SFT</b></div></div>
        <div className="rule-section"><div className="rule-title"><span style={{ background: '#fff0f5', color: '#ec4899' }}><Tag size={15} /></span><div><b>Discount Rules</b></div></div><div className="rule-line"><span>Up to 100 SFT</span><b>{rules.discount_upto_100}%</b></div><div className="rule-line"><span>100 - 300 SFT</span><b>{rules.discount_100_300}%</b></div><div className="rule-line"><span>Above 300 SFT</span><b>{rules.discount_above_300}%</b></div></div>
        <Button tone="secondary" style={{ width: '100%', marginTop: 10 }} onClick={() => setRulesOpen(true)}><Edit3 size={14} /> Edit Pricing Rules</Button>
      </>}</Card>
    </div>

    <Modal open={itemOpen} onClose={() => setItemOpen(false)} title={editing ? 'Edit Catalog Item' : 'Add Catalog Item'} width={860}>
      <form onSubmit={saveItem}>
        <div className="form-grid three">
          <Field label="Category"><Select value={form.category} onChange={e => setForm({ ...form, category: e.target.value })}>{productCategories.map(item => <option key={item}>{item}</option>)}</Select></Field>
          <Field label="Product Type"><Select value={form.product_type} onChange={e => setForm({ ...form, product_type: e.target.value })}>{productTypes.map(item => <option key={item}>{item}</option>)}</Select></Field>
          <Field label="Name" required><Input required value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} /></Field>
          <Field label="Subtitle"><Input value={form.subtitle} onChange={e => setForm({ ...form, subtitle: e.target.value })} /></Field>
          <Field label="Profile Brand"><Input value={form.profile_brand} onChange={e => setForm({ ...form, profile_brand: e.target.value })} /></Field>
          <Field label="Profile Series"><Input value={form.profile_series} onChange={e => setForm({ ...form, profile_series: e.target.value })} /></Field>
          <Field label="Profile Display"><Input value={form.profile} onChange={e => setForm({ ...form, profile: e.target.value })} /></Field>
          <Field label="Track"><Input value={form.track} onChange={e => setForm({ ...form, track: e.target.value })} /></Field>
          <Field label="Color"><Input value={form.color} onChange={e => setForm({ ...form, color: e.target.value })} /></Field>
          <Field label="Glass Type"><Input value={form.glass_type} onChange={e => setForm({ ...form, glass_type: e.target.value })} /></Field>
          <Field label="Glass Thickness"><Input value={form.glass_thickness} onChange={e => setForm({ ...form, glass_thickness: e.target.value })} /></Field>
          <Field label="Glass Color"><Input value={form.glass_color} onChange={e => setForm({ ...form, glass_color: e.target.value })} /></Field>
          <Field label="Glass Display"><Input value={form.glass} onChange={e => setForm({ ...form, glass: e.target.value })} /></Field>
          <Field label="Hardware"><Input value={form.hardware} onChange={e => setForm({ ...form, hardware: e.target.value })} /></Field>
          <Field label="Reinforcement"><Input value={form.reinforcement} onChange={e => setForm({ ...form, reinforcement: e.target.value })} /></Field>
          <Field label="Mesh"><Input value={form.mesh} onChange={e => setForm({ ...form, mesh: e.target.value })} /></Field>
          <Field label="HSN Code"><Input value={form.hsn_code} onChange={e => setForm({ ...form, hsn_code: e.target.value })} /></Field>
          <Field label="Min Billable SFT"><Input type="number" step="0.01" value={Number(form.min_billable_sft)} onChange={e => setForm({ ...form, min_billable_sft: Number(e.target.value) })} /></Field>
          <Field label="Rate / SFT"><Input type="number" step="0.01" value={Number(form.rate_per_sft)} onChange={e => setForm({ ...form, rate_per_sft: Number(e.target.value) })} /></Field>
          <Field label="GST %"><Input type="number" step="0.01" value={Number(form.gst_percent)} onChange={e => setForm({ ...form, gst_percent: Number(e.target.value) })} /></Field>
          <Field label="Installation / SFT"><Input type="number" step="0.01" value={Number(form.installation_rate)} onChange={e => setForm({ ...form, installation_rate: Number(e.target.value) })} /></Field>
          <Field label="Rounding Rule"><Select value={form.rounding_rule} onChange={e => setForm({ ...form, rounding_rule: e.target.value })}>{roundingRules.map(item => <option key={item}>{item}</option>)}</Select></Field>
          <Field label="Status"><Select value={form.status} onChange={e => setForm({ ...form, status: e.target.value })}><option>Active</option><option>Inactive</option></Select></Field>
        </div>
        <div className="form-actions"><Button type="button" tone="secondary" onClick={() => setItemOpen(false)}>Cancel</Button><Button type="submit">Save Item</Button></div>
      </form>
    </Modal>

    <Modal open={rulesOpen} onClose={() => setRulesOpen(false)} title="Edit Pricing Rules" width={760}>{rules && <form onSubmit={saveRules}><div className="form-grid three">{Object.entries(rules).filter(([key]) => key !== 'id').map(([key, value]) => <Field key={key} label={key.replaceAll('_', ' ').replace(/\b\w/g, char => char.toUpperCase())}>{['rounding_rule', 'tax_type'].includes(key) ? <Input value={String(value)} onChange={e => setRules({ ...rules, [key]: e.target.value })} /> : <Input type="number" step="0.01" value={Number(value)} onChange={e => setRules({ ...rules, [key]: Number(e.target.value) })} />}</Field>)}</div><div className="form-actions"><Button type="button" tone="secondary" onClick={() => setRulesOpen(false)}>Cancel</Button><Button type="submit">Save Rules</Button></div></form>}</Modal>
  </>;
}
