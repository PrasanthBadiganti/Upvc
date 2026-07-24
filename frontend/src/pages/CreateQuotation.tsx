import { FormEvent, useEffect, useMemo, useState } from 'react';
import { Boxes, CircleDot, DoorOpen, FileDown, Grid3X3, Layers3, Palette, Plus, Save, Send, Shield, Trash2, UserPlus2 } from 'lucide-react';
import { useNavigate, useParams } from 'react-router-dom';
import api from '../api';
import { Button, Card, Field, Input, Modal, PageHeader, Select } from '../components/UI';
import { CatalogItem, Customer, QuotationItem } from '../types';
import { currency, INDIAN_STATES } from '../utils';

const emptyItem = (): QuotationItem => ({catalog_item_id:null,category:'',style:'',width_mm:0,height_mm:0,sft:0,quantity:1,total_sft:0,rate_per_sft:0,amount:0,location:''});

const blankNewCustomer = {name:'',phone:'',email:'',address:'',gst_number:'',state:'',project_site:''};

export default function CreateQuotation() {
  const navigate = useNavigate();
  const { id } = useParams();
  const quoteId = id ? Number(id) : 0;
  const isEditing = Boolean(quoteId);
  const [customers,setCustomers] = useState<Customer[]>([]);
  const [catalog,setCatalog] = useState<CatalogItem[]>([]);
  const [customerId,setCustomerId] = useState<number>(0);
  const [items,setItems] = useState<QuotationItem[]>([emptyItem()]);
  const [transport,setTransport] = useState(0);
  const [discount,setDiscount] = useState(0);
  const [status,setStatus] = useState('Draft');
  const [saving,setSaving] = useState(false);
  const [form,setForm] = useState({quotation_date:'',validity_days:0,sales_person:'',site_location:'',address:'',notes:''});
  const [newCustomerOpen,setNewCustomerOpen] = useState(false);
  const [newCustomer,setNewCustomer] = useState(blankNewCustomer);
  const [newCustomerSaving,setNewCustomerSaving] = useState(false);
  useEffect(()=>{ api.get('/customers').then(r=>setCustomers(r.data)); api.get('/catalog',{params:{status:'Active'}}).then(r=>setCatalog(r.data)); },[]);
  useEffect(()=>{
    if(!quoteId) return;
    api.get(`/quotations/${quoteId}`).then(({data})=>{
      if(['Accepted','Converted'].includes(data.status)) {
        navigate(`/quotations/${quoteId}`);
        return;
      }
      setCustomerId(data.customer_id);
      setStatus(data.status);
      setTransport(Number(data.transport));
      setDiscount(Number(data.discount));
      setForm({quotation_date:data.quotation_date,validity_days:data.validity_days,sales_person:data.sales_person,site_location:data.site_location,address:data.address,notes:data.notes});
      setItems(data.items.map((item:QuotationItem)=>({
        ...item,
        catalog_item_id:item.catalog_item_id || null,
        width_mm:Number(item.width_mm),
        height_mm:Number(item.height_mm),
        sft:Number(item.sft),
        quantity:Number(item.quantity),
        total_sft:Number(item.total_sft),
        rate_per_sft:Number(item.rate_per_sft),
        amount:Number(item.amount),
      })));
    });
  },[quoteId,navigate]);

  const totals = useMemo(()=>{
    const subtotal = items.reduce((s,i)=>s+Number(i.amount||0),0);
    const taxable = subtotal + transport - discount;
    const gst = taxable*.18;
    const grand = taxable+gst;
    return {subtotal,taxable,gst,grand,advance:grand*.5,balance:grand*.5,totalSft:items.reduce((s,i)=>s+Number(i.total_sft||0),0)};
  },[items,transport,discount]);

  const update = (index:number,key:keyof QuotationItem,value:string|number) => {
    setItems(prev=>prev.map((row,i)=>{
      if(i!==index) return row;
      const stringFields = ['category','style','location','profile','color','track','glass','glass_color','hardware','reinforcement','mesh','hsn_code'];
      const next={...row,[key]: typeof value==='string' && stringFields.includes(String(key)) ? value : Number(value)} as QuotationItem;
      if(['width_mm','height_mm'].includes(String(key))) next.sft = Math.max(0, Math.ceil((next.width_mm/304.8)*(next.height_mm/304.8)));
      const selectedCatalog = catalog.find(item => item.id === next.catalog_item_id);
      const minSft = Number(selectedCatalog?.min_billable_sft || 0);
      next.total_sft = Number((Math.max(Number(next.sft || 0), minSft)*next.quantity).toFixed(2));
      next.amount = Number((next.total_sft*next.rate_per_sft).toFixed(2));
      return next;
    }));
  };

  const applyCatalog = (index:number,catalogId:number) => {
    const selectedItem = catalog.find(item=>item.id===catalogId);
    if(!selectedItem) return;
    setItems(prev=>prev.map((row,i)=>{
      if(i!==index) return row;
      const sft = Number(row.sft || Math.ceil((row.width_mm/304.8)*(row.height_mm/304.8)));
      const totalSft = Number((Math.max(sft, Number(selectedItem.min_billable_sft || 0))*row.quantity).toFixed(2));
      return {
        ...row,
        catalog_item_id: selectedItem.id,
        category: selectedItem.name,
        style: selectedItem.product_type,
        total_sft: totalSft,
        rate_per_sft: Number(selectedItem.rate_per_sft),
        amount: Number((totalSft*Number(selectedItem.rate_per_sft)).toFixed(2)),
        hsn_code: selectedItem.hsn_code,
        profile: selectedItem.profile,
        color: selectedItem.color,
        track: selectedItem.track,
        glass: selectedItem.glass,
        glass_color: selectedItem.glass_color,
        hardware: selectedItem.hardware,
        reinforcement: selectedItem.reinforcement,
        mesh: selectedItem.mesh,
      };
    }));
  };

  const save = async (send=false) => {
    if(!customerId || !form.sales_person || !form.quotation_date || !form.validity_days) return;
    setSaving(true);
    try {
      const selected=customers.find(c=>c.id===customerId);
      const payload={customer_id:customerId,...form,status:send?'Sent':status,transport,discount,items,address:form.address || selected?.address || ''};
      const {data}=isEditing ? await api.put(`/quotations/${quoteId}`,payload) : await api.post('/quotations',payload);
      navigate(isEditing ? `/quotations/${data.id}` : '/quotations',{state:{created:data.number}});
    } finally { setSaving(false); }
  };

  const submitNewCustomer = async (e:FormEvent) => {
    e.preventDefault();
    if(!newCustomer.name) return;
    setNewCustomerSaving(true);
    try {
      const {data} = await api.post('/customers',{...newCustomer,assigned_to:form.sales_person || undefined,status:'New'});
      setCustomers(prev=>[...prev,data]);
      setCustomerId(data.id);
      setForm(f=>({...f,address:f.address || data.address,site_location:f.site_location || data.project_site}));
      setNewCustomerOpen(false);
      setNewCustomer(blankNewCustomer);
    } finally { setNewCustomerSaving(false); }
  };

  const selected=customers.find(c=>c.id===customerId);
  const specSource = items.find(item => item.catalog_item_id) || items[0];
  return <>
    <PageHeader title={isEditing?'Edit Quotation':'Create Quotation'} subtitle={isEditing?'Update draft or sent quotation':'Quotations / New Quotation'} />
    <div className="quotation-layout">
      <div className="quote-main">
        <Card className="quote-form-card">
          <h3>Customer Details</h3>
          <div className="customer-form-grid">
            <Field label="Customer Name" required>
              <div style={{display:'flex',gap:8}}>
                <Select required style={{flex:1}} value={customerId} onChange={e=>setCustomerId(Number(e.target.value))}>
                  <option value={0} disabled>Select customer...</option>
                  {customers.map(c=><option key={c.id} value={c.id}>{c.name}</option>)}
                </Select>
                <button type="button" className="icon-btn" title="Onboard new customer" onClick={()=>setNewCustomerOpen(true)}><UserPlus2 size={17}/></button>
              </div>
            </Field>
            <Field label="Phone"><Input readOnly value={selected?.phone||''}/></Field>
            <Field label="Site Location"><Input value={form.site_location} onChange={e=>setForm({...form,site_location:e.target.value})}/></Field>
            <Field label="Sales Person" required><Select required value={form.sales_person} onChange={e=>setForm({...form,sales_person:e.target.value})}><option value="" disabled>Select sales person...</option><option>Arun Verma</option><option>Neha Kapoor</option><option>Rohit Singh</option></Select></Field>
            <Field label="Address"><Input value={form.address} onChange={e=>setForm({...form,address:e.target.value})}/></Field>
            <Field label="Quotation Date" required><Input type="date" required value={form.quotation_date} onChange={e=>setForm({...form,quotation_date:e.target.value})}/></Field>
            <Field label="Validity" required><Select required value={form.validity_days || ''} onChange={e=>setForm({...form,validity_days:Number(e.target.value)})}><option value="" disabled>Select validity...</option><option value={15}>15 Days</option><option value={30}>30 Days</option><option value={45}>45 Days</option></Select></Field>
            <Field label="Status"><Select value={status} onChange={e=>setStatus(e.target.value)}><option>Draft</option><option>Sent</option><option>Accepted</option></Select></Field>
          </div>
        </Card>

        <Card className="quote-items-card">
          <div className="quote-items-toolbar"><h3>Quotation Items</h3><div className="quote-items-actions"><Button tone="secondary"><FileDown size={15}/> Import from Excel</Button><Button onClick={()=>setItems([...items,emptyItem()])}><Plus size={15}/> Add Item</Button></div></div>
          <div className="table-wrap"><table className="data-table editable-table"><thead><tr><th>S.No</th><th>Price Master</th><th>Category</th><th>Style</th><th>HSN</th><th>Width (mm)</th><th>Height (mm)</th><th>SFT</th><th>Qty</th><th>Total SFT</th><th>Rate / SFT (Rs.)</th><th>Amount (Rs.)</th><th>Location</th><th>Action</th></tr></thead><tbody>{items.map((row,i)=><tr key={i}>
            <td>{i+1}</td>
            <td><select value={row.catalog_item_id || ''} onChange={e=>applyCatalog(i,Number(e.target.value))}><option value="">Manual</option>{catalog.map(item=><option key={item.id} value={item.id}>{item.name} - {currency(item.rate_per_sft)}</option>)}</select></td>
            <td><input value={row.category} onChange={e=>update(i,'category',e.target.value)}/></td><td><input value={row.style} onChange={e=>update(i,'style',e.target.value)}/></td>
            <td><input value={row.hsn_code||''} onChange={e=>update(i,'hsn_code',e.target.value)}/></td>
            <td><input type="number" placeholder="0" value={row.width_mm || ''} onChange={e=>update(i,'width_mm',e.target.value)}/></td><td><input type="number" placeholder="0" value={row.height_mm || ''} onChange={e=>update(i,'height_mm',e.target.value)}/></td>
            <td><input type="number" placeholder="0" value={row.sft || ''} onChange={e=>update(i,'sft',e.target.value)}/></td><td><input type="number" value={row.quantity} onChange={e=>update(i,'quantity',e.target.value)}/></td>
            <td>{row.total_sft.toFixed(2)}</td><td><input type="number" placeholder="0" value={row.rate_per_sft || ''} onChange={e=>update(i,'rate_per_sft',e.target.value)}/></td><td className="amount">{currency(row.amount,2)}</td>
            <td><input value={row.location} onChange={e=>update(i,'location',e.target.value)}/></td><td><button className="delete-mini" onClick={()=>setItems(items.filter((_,x)=>x!==i))}><Trash2 size={14}/></button></td>
          </tr>)}</tbody></table></div>
          <div className="quote-table-footer"><Button tone="ghost" onClick={()=>setItems([...items,emptyItem()])}><Plus size={14}/> Add New Item</Button><div><b>Total SFT&nbsp;&nbsp; {totals.totalSft.toFixed(2)}</b>&nbsp;&nbsp;&nbsp;&nbsp;<b>{currency(totals.subtotal,2)}</b></div></div>
        </Card>

        <div className="spec-grid">
          {[
            [Layers3,'Profile',specSource?.profile || 'Manual','Price master material'],[Palette,'Color',specSource?.color || 'Manual','Selected finish'],[DoorOpen,'Track',specSource?.track || 'Manual','Track / opening system'],[Grid3X3,'Glass',specSource?.glass || 'Manual','Glass specification'],
            [CircleDot,'Glass Color',specSource?.glass_color || 'Manual','Selected tint'],[Shield,'Hardware',specSource?.hardware || 'Manual','Hardware set'],[Boxes,'Reinforcement',specSource?.reinforcement || 'Manual','Internal support'],[Grid3X3,'Mesh',specSource?.mesh || 'Manual','Mesh option']
          ].map(([Icon,label,value,desc],i)=>{const I=Icon as typeof Layers3; return <div className="spec-card" key={i}><I className="spec-icon" size={23}/><div><small>{String(label)}</small><b>{String(value)}</b><em>{String(desc)}</em></div></div>})}
        </div>
        <Card className="quote-notes"><small>Notes / Special Instructions (Optional)</small><textarea className="input" placeholder="Add any notes or special instructions..." value={form.notes} onChange={e=>setForm({...form,notes:e.target.value})}/></Card>
      </div>

      <aside>
        <Card className="quote-summary">
          <h3>Quotation Summary</h3>
          <div className="summary-line"><span>Subtotal</span><span>{currency(totals.subtotal,2)}</span></div>
          <div className="summary-line"><span>Transport</span><Input type="number" placeholder="0" value={transport || ''} onChange={e=>setTransport(Number(e.target.value))} style={{width:105,height:31,textAlign:'right'}}/></div>
          <div className="summary-line"><span>Discount</span><Input type="number" placeholder="0" value={discount || ''} onChange={e=>setDiscount(Number(e.target.value))} style={{width:105,height:31,textAlign:'right',color:'#0eaf72'}}/></div>
          <div className="summary-line"><span>Taxable Amount</span><span>{currency(totals.taxable,2)}</span></div>
          <div className="summary-line"><span>GST (18%)</span><span>{currency(totals.gst,2)}</span></div>
          <div className="summary-line total"><span>Grand Total</span><span>{currency(totals.grand,2)}</span></div>
          <div className="summary-line"><span>Advance (50%)</span><span>{currency(totals.advance,2)}</span></div>
          <div className="summary-line balance"><span>Balance Due</span><span>{currency(totals.balance,2)}</span></div>
          <div className="payment-terms"><h4>Payment Terms</h4><div className="terms-circles"><div><div className="term-circle">50%</div><b>Advance</b><small>On Confirmation</small></div><div><div className="term-circle amber">40%</div><b>During Production</b><small>Before Dispatch</small></div><div><div className="term-circle blue">10%</div><b>On Installation</b><small>After Completion</small></div></div></div>
          <div className="conditions"><h4>Terms & Conditions</h4><p>This quotation is valid for the period mentioned above.</p><p>GST as applicable will be charged extra.</p><p>Installation & Fixing as per standard scope.</p><p>Any changes in dimensions may affect the price.</p><p>Payment to be made as per terms mentioned.</p></div>
        </Card>
          <div className="quote-actionbar"><Button tone="secondary" onClick={()=>save(false)} disabled={saving}><Save size={15}/> {isEditing?'Save Changes':'Save Draft'}</Button><Button tone="secondary" onClick={()=>window.print()}><FileDown size={15}/> Preview PDF</Button><Button onClick={()=>save(true)} disabled={saving}><Send size={15}/> Send Quotation</Button></div>
      </aside>
    </div>

    <Modal open={newCustomerOpen} onClose={()=>setNewCustomerOpen(false)} title="Onboard New Customer" width={640}>
      <form onSubmit={submitNewCustomer}>
        <div className="form-grid">
          <Field label="Customer Name" required><Input required value={newCustomer.name} onChange={e=>setNewCustomer({...newCustomer,name:e.target.value})}/></Field>
          <Field label="Phone"><Input value={newCustomer.phone} onChange={e=>setNewCustomer({...newCustomer,phone:e.target.value})}/></Field>
          <Field label="Email"><Input type="email" value={newCustomer.email} onChange={e=>setNewCustomer({...newCustomer,email:e.target.value})}/></Field>
          <Field label="GST Number"><Input value={newCustomer.gst_number} onChange={e=>setNewCustomer({...newCustomer,gst_number:e.target.value})}/></Field>
          <Field label="State"><Select value={newCustomer.state} onChange={e=>setNewCustomer({...newCustomer,state:e.target.value})}><option value="">Select state</option>{INDIAN_STATES.map(s=><option key={s}>{s}</option>)}</Select></Field>
          <Field label="Project / Site"><Input value={newCustomer.project_site} onChange={e=>setNewCustomer({...newCustomer,project_site:e.target.value})}/></Field>
          <Field label="Address"><textarea className="input" value={newCustomer.address} onChange={e=>setNewCustomer({...newCustomer,address:e.target.value})}/></Field>
        </div>
        <div className="form-actions"><Button type="button" tone="secondary" onClick={()=>setNewCustomerOpen(false)}>Cancel</Button><Button type="submit" disabled={newCustomerSaving}><UserPlus2 size={14}/> Save &amp; Select Customer</Button></div>
      </form>
    </Modal>
  </>;
}
