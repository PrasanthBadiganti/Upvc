import { FormEvent, useEffect, useMemo, useState } from 'react';
import { Edit3, PackagePlus, Percent, Search, Settings2, Tag, Truck, Wrench } from 'lucide-react';
import api from '../api';
import { Button, Card, Field, Input, Loading, Modal, PageHeader, Select } from '../components/UI';
import Status from '../components/Status';
import { CatalogItem, PricingRule } from '../types';
import { currency } from '../utils';

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
  const [itemOpen, setItemOpen] = useState(false);
  const [rulesOpen, setRulesOpen] = useState(false);
  const [editing, setEditing] = useState<CatalogItem | null>(null);
  const [form, setForm] = useState<CatalogForm>(blankItem);
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 10;

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

  useEffect(() => { load(); setCurrentPage(1); }, [search, category, productType, status]);

  const summary = useMemo(() => ({
    active: items.filter(item => item.status === 'Active').length,
    categories: Array.from(new Set(items.map(item => item.category))).length,
    avgRate: items.length ? items.reduce((sum, item) => sum + Number(item.rate_per_sft || 0), 0) / items.length : 0,
  }), [items]);

  const paginatedItems = useMemo(() => {
    const start = (currentPage - 1) * pageSize;
    return items.slice(start, start + pageSize);
  }, [items, currentPage, pageSize]);

  const totalPages = Math.ceil(items.length / pageSize);

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
    if (!form.name || !form.profile) {
      alert('Please fill: Name and Profile');
      return;
    }
    if (form.hsn_code && form.hsn_code.length !== 8) {
      alert('HSN Code must be 8 digits (e.g., 70071900)');
      return;
    }
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
    <PageHeader title="Catalog & Price Master" subtitle="Manage UPVC products and pricing" />

    <Card className="catalog-main">
      <div style={{display:'flex',alignItems:'center',justifyContent:'space-between',marginBottom:16}}>
        <h3 style={{margin:0}}>Products</h3>
        <div style={{display:'flex',gap:8}}>
          <Button onClick={showAdd}><PackagePlus size={16} /> Add Product</Button>
          <Button tone="secondary" onClick={() => setRulesOpen(true)}><Settings2 size={16} /> Business Rules</Button>
        </div>
      </div>

      <div className="catalog-filters">
        <Field label="Category"><Select value={category} onChange={e => setCategory(e.target.value)}><option value="">All Categories</option>{productCategories.map(item => <option key={item}>{item}</option>)}</Select></Field>
        <Field label="Product Type"><Select value={productType} onChange={e => setProductType(e.target.value)}><option value="">All Types</option>{productTypes.map(item => <option key={item}>{item}</option>)}</Select></Field>
        <Field label="Status"><Select value={status} onChange={e => setStatus(e.target.value)}><option value="">All Status</option><option>Active</option><option>Inactive</option></Select></Field>
        <div className="search-box"><Search size={16} /><input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search product, profile, glass..." /></div>
      </div>

      {loading ? <Loading /> : (
        <div className="table-wrap"><table className="data-table"><thead><tr><th>Product</th><th>Profile</th><th>Glass</th><th>Rate / SFT</th><th>HSN Code</th><th>Status</th><th style={{textAlign:'center',width:'140px'}}>Actions</th></tr></thead><tbody>{paginatedItems.map(item => <tr key={item.id}>
          <td><span className="cell-title">{item.name}</span><span className="cell-sub">{item.category} / {item.product_type}</span></td>
          <td><span className="material-chip">{item.profile_brand || item.profile}</span><span className="cell-sub">{item.profile_series || item.track}</span></td>
          <td><span className="material-chip green">{item.glass_type || item.glass}</span><span className="cell-sub">{item.glass_thickness}</span></td>
          <td className="amount success"><b>{currency(item.rate_per_sft)}</b></td>
          <td><span className={item.hsn_code && item.hsn_code.length === 8 ? 'material-chip blue' : 'muted'}>{item.hsn_code || 'Not set'}</span></td>
          <td><Status value={item.status} /></td>
          <td style={{textAlign:'center',display:'flex',gap:4,justifyContent:'center'}}><button className="mini-button" title="Edit" onClick={() => showEdit(item)}><Edit3 size={14} /></button></td>
        </tr>)}
        {!items.length && <tr><td colSpan={7} className="muted">No products found</td></tr>}
        </tbody></table></div>
      )}

      <div style={{display:'flex',alignItems:'center',justifyContent:'space-between',padding:'12px 0',fontSize:'12.5px',color:'#60708a',borderTop:'1px solid #edf1f5'}}>
        <span>{items.length} total | {summary.active} active | {summary.categories} categories | Avg rate {currency(summary.avgRate)}</span>
        <div style={{display:'flex',gap:8,alignItems:'center'}}>
          <span>Page {currentPage} of {totalPages || 1}</span>
          <button onClick={() => setCurrentPage(Math.max(1, currentPage - 1))} disabled={currentPage === 1} style={{padding:'4px 12px',border:'1px solid #dbe3ed',borderRadius:'5px',background:'#fff',cursor:currentPage === 1 ? 'not-allowed' : 'pointer',opacity:currentPage === 1 ? 0.5 : 1}}>← Prev</button>
          <button onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))} disabled={currentPage === totalPages} style={{padding:'4px 12px',border:'1px solid #dbe3ed',borderRadius:'5px',background:'#fff',cursor:currentPage === totalPages ? 'not-allowed' : 'pointer',opacity:currentPage === totalPages ? 0.5 : 1}}>Next →</button>
        </div>
      </div>
    </Card>

    <Modal open={itemOpen} onClose={() => setItemOpen(false)} title={editing ? 'Edit Product' : 'Add Product'} width={720}>
      <form onSubmit={saveItem}>
        <div style={{marginBottom:16}}><b style={{fontSize:13,color:'#40506a',textTransform:'uppercase',letterSpacing:'0.05em'}}>Basic Info</b></div>
        <div className="form-grid">
          <Field label="Category" required><Select required value={form.category} onChange={e => setForm({ ...form, category: e.target.value })}>{productCategories.map(item => <option key={item}>{item}</option>)}</Select></Field>
          <Field label="Product Type" required><Select required value={form.product_type} onChange={e => setForm({ ...form, product_type: e.target.value })}>{productTypes.map(item => <option key={item}>{item}</option>)}</Select></Field>
          <Field label="Product Name" required><Input required value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} placeholder="e.g., Sliding Window 60mm" /></Field>
          <Field label="Subtitle"><Input value={form.subtitle} onChange={e => setForm({ ...form, subtitle: e.target.value })} placeholder="Optional description" /></Field>
        </div>

        <div style={{marginBottom:16,marginTop:20}}><b style={{fontSize:13,color:'#40506a',textTransform:'uppercase',letterSpacing:'0.05em'}}>Materials & Specs</b></div>
        <div className="form-grid">
          <Field label="Profile Brand"><Input value={form.profile_brand} onChange={e => setForm({ ...form, profile_brand: e.target.value })} placeholder="e.g., VEKA" /></Field>
          <Field label="Profile Series"><Input value={form.profile_series} onChange={e => setForm({ ...form, profile_series: e.target.value })} placeholder="e.g., Euroline 60" /></Field>
          <Field label="Profile Display" required><Input required value={form.profile} onChange={e => setForm({ ...form, profile: e.target.value })} placeholder="e.g., VEKA 60mm" /></Field>
          <Field label="Track"><Input value={form.track} onChange={e => setForm({ ...form, track: e.target.value })} placeholder="e.g., 2 Track" /></Field>
          <Field label="Glass Type"><Input value={form.glass_type} onChange={e => setForm({ ...form, glass_type: e.target.value })} placeholder="e.g., Toughened" /></Field>
          <Field label="Glass Thickness"><Input value={form.glass_thickness} onChange={e => setForm({ ...form, glass_thickness: e.target.value })} placeholder="e.g., 5mm" /></Field>
          <Field label="Glass Color"><Input value={form.glass_color} onChange={e => setForm({ ...form, glass_color: e.target.value })} placeholder="e.g., Clear" /></Field>
          <Field label="Glass Display"><Input value={form.glass} onChange={e => setForm({ ...form, glass: e.target.value })} placeholder="e.g., 5MM Saint Gobain" /></Field>
          <Field label="Hardware"><Input value={form.hardware} onChange={e => setForm({ ...form, hardware: e.target.value })} placeholder="e.g., McCoy" /></Field>
          <Field label="Reinforcement"><Input value={form.reinforcement} onChange={e => setForm({ ...form, reinforcement: e.target.value })} placeholder="e.g., 1.5mm GI" /></Field>
          <Field label="Mesh"><Input value={form.mesh} onChange={e => setForm({ ...form, mesh: e.target.value })} placeholder="e.g., SS Mesh" /></Field>
          <Field label="Color"><Input value={form.color} onChange={e => setForm({ ...form, color: e.target.value })} placeholder="e.g., White" /></Field>
        </div>

        <div style={{marginBottom:16,marginTop:20}}><b style={{fontSize:13,color:'#40506a',textTransform:'uppercase',letterSpacing:'0.05em'}}>Tax & Pricing</b></div>
        <div className="form-grid">
          <Field label="HSN Code (8 digits)" required><Input required maxLength={8} pattern="[0-9]{8}" value={form.hsn_code} onChange={e => setForm({ ...form, hsn_code: e.target.value.slice(0, 8) })} placeholder="e.g., 70071900" title="Must be 8 digits" /></Field>
          <Field label="GST %"><Input type="number" step="0.01" value={Number(form.gst_percent)} onChange={e => setForm({ ...form, gst_percent: Number(e.target.value) })} /></Field>
          <Field label="Min Billable SFT"><Input type="number" step="0.01" value={Number(form.min_billable_sft)} onChange={e => setForm({ ...form, min_billable_sft: Number(e.target.value) })} /></Field>
          <Field label="Rate / SFT"><Input type="number" step="0.01" value={Number(form.rate_per_sft)} onChange={e => setForm({ ...form, rate_per_sft: Number(e.target.value) })} placeholder="Price per square foot" /></Field>
          <Field label="Installation / SFT"><Input type="number" step="0.01" value={Number(form.installation_rate)} onChange={e => setForm({ ...form, installation_rate: Number(e.target.value) })} placeholder="Installation charge per SFT" /></Field>
          <Field label="Rounding Rule"><Select value={form.rounding_rule} onChange={e => setForm({ ...form, rounding_rule: e.target.value })}>{roundingRules.map(item => <option key={item}>{item}</option>)}</Select></Field>
          <Field label="Status"><Select value={form.status} onChange={e => setForm({ ...form, status: e.target.value })}><option>Active</option><option>Inactive</option></Select></Field>
        </div>

        <div className="form-actions"><Button type="button" tone="secondary" onClick={() => setItemOpen(false)}>Cancel</Button><Button type="submit">Save Product</Button></div>
      </form>
    </Modal>

    <Modal open={rulesOpen} onClose={() => setRulesOpen(false)} title="Business Rules & Pricing Defaults" width={680}>{rules && <form onSubmit={saveRules}><div style={{maxHeight:'60vh',overflowY:'auto'}}>
      <div style={{marginBottom:20}}><b style={{fontSize:12,color:'#60708a',textTransform:'uppercase',letterSpacing:'0.05em'}}>Transport Charges</b>
        <div className="form-grid" style={{marginTop:12}}>
          <Field label="Within City"><Input type="number" step="0.01" value={Number(rules.within_city_transport)} onChange={e => setRules({ ...rules, within_city_transport: Number(e.target.value) })} /></Field>
          <Field label="Beyond City"><Input type="number" step="0.01" value={Number(rules.beyond_city_transport)} onChange={e => setRules({ ...rules, beyond_city_transport: Number(e.target.value) })} /></Field>
        </div>
      </div>

      <div style={{marginBottom:20}}><b style={{fontSize:12,color:'#60708a',textTransform:'uppercase',letterSpacing:'0.05em'}}>Minimum Billing</b>
        <div className="form-grid" style={{marginTop:12}}>
          <Field label="Minimum SFT"><Input type="number" step="0.01" value={Number(rules.minimum_billable_sft)} onChange={e => setRules({ ...rules, minimum_billable_sft: Number(e.target.value) })} /></Field>
          <Field label="Rounding Rule"><Input value={String(rules.rounding_rule)} onChange={e => setRules({ ...rules, rounding_rule: e.target.value })} /></Field>
        </div>
      </div>

      <div style={{marginBottom:20}}><b style={{fontSize:12,color:'#60708a',textTransform:'uppercase',letterSpacing:'0.05em'}}>GST & Tax</b>
        <div className="form-grid" style={{marginTop:12}}>
          <Field label="GST Rate %"><Input type="number" step="0.01" value={Number(rules.gst_rate)} onChange={e => setRules({ ...rules, gst_rate: Number(e.target.value) })} /></Field>
          <Field label="Tax Type"><Input value={String(rules.tax_type)} onChange={e => setRules({ ...rules, tax_type: e.target.value })} /></Field>
        </div>
      </div>

      <div style={{marginBottom:20}}><b style={{fontSize:12,color:'#60708a',textTransform:'uppercase',letterSpacing:'0.05em'}}>Installation Charges</b>
        <div className="form-grid" style={{marginTop:12}}>
          <Field label="Standard / SFT"><Input type="number" step="0.01" value={Number(rules.installation_standard)} onChange={e => setRules({ ...rules, installation_standard: Number(e.target.value) })} /></Field>
          <Field label="Above 200 SFT / SFT"><Input type="number" step="0.01" value={Number(rules.installation_above_200)} onChange={e => setRules({ ...rules, installation_above_200: Number(e.target.value) })} /></Field>
        </div>
      </div>

      <div style={{marginBottom:20}}><b style={{fontSize:12,color:'#60708a',textTransform:'uppercase',letterSpacing:'0.05em'}}>Discount Rules</b>
        <div className="form-grid" style={{marginTop:12}}>
          <Field label="Up to 100 SFT %"><Input type="number" step="0.01" value={Number(rules.discount_upto_100)} onChange={e => setRules({ ...rules, discount_upto_100: Number(e.target.value) })} /></Field>
          <Field label="100-300 SFT %"><Input type="number" step="0.01" value={Number(rules.discount_100_300)} onChange={e => setRules({ ...rules, discount_100_300: Number(e.target.value) })} /></Field>
          <Field label="Above 300 SFT %"><Input type="number" step="0.01" value={Number(rules.discount_above_300)} onChange={e => setRules({ ...rules, discount_above_300: Number(e.target.value) })} /></Field>
        </div>
      </div>
    </div><div className="form-actions"><Button type="button" tone="secondary" onClick={() => setRulesOpen(false)}>Cancel</Button><Button type="submit">Save Rules</Button></div></form>}</Modal>
  </>;
}
