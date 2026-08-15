import { FormEvent, useEffect, useMemo, useState } from 'react';
import { Boxes, ChevronDown, ChevronUp, CircleDot, Copy, DoorOpen, Download, FileDown, Grid3X3, Layers3, Palette, Plus, Save, Send, Shield, Trash2, UserPlus2, Eye, X } from 'lucide-react';
import { useNavigate, useParams } from 'react-router-dom';
import api from '../api';
import { Button, Card, Field, Input, Modal, PageHeader, Select } from '../components/UI';
import { CatalogItem, Customer, QuotationItem } from '../types';
import { currency, INDIAN_STATES } from '../utils';
import { useToastContext } from '../contexts/ToastContext';
import { useKeyboardShortcut, SHORTCUTS } from '../hooks/useKeyboardShortcut';

const emptyItem = (): QuotationItem => ({catalog_item_id:null,category:'',style:'',width_mm:0,height_mm:0,sft:0,quantity:1,total_sft:0,rate_per_sft:0,amount:0,location:''});

const blankNewCustomer = {name:'',phone:'',email:'',address:'',gst_number:'',state:'',project_site:''};

export default function CreateQuotation() {
  const navigate = useNavigate();
  const { id } = useParams();
  const toast = useToastContext();
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
  const [expandedRow,setExpandedRow] = useState<number | null>(null);
  const [specModalOpen,setSpecModalOpen] = useState(false);
  const [specModalIndex,setSpecModalIndex] = useState<number | null>(null);

  useKeyboardShortcut([
    { ...SHORTCUTS.SAVE, onPress: () => save(false), disabled: saving },
    { key: 'Enter', ctrl: true, onPress: () => save(true), disabled: saving },
  ]);
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
    if(!customerId || !form.sales_person || !form.quotation_date || !form.validity_days) {
      toast.warning('Please fill all required fields');
      return;
    }
    setSaving(true);
    try {
      const selected=customers.find(c=>c.id===customerId);
      const payload={customer_id:customerId,...form,status:send?'Sent':status,transport,discount,items,address:form.address || selected?.address || ''};
      const {data}=isEditing ? await api.put(`/quotations/${quoteId}`,payload) : await api.post('/quotations',payload);
      toast.success(send ? `Quotation sent to ${selected?.name}!` : 'Quotation saved as draft');
      navigate(isEditing ? `/quotations/${data.id}` : '/quotations',{state:{created:data.number}});
    } catch (err) {
      toast.error('Failed to save quotation');
    } finally { setSaving(false); }
  };

  const submitNewCustomer = async (e:FormEvent) => {
    e.preventDefault();
    if(!newCustomer.name || !newCustomer.state) {
      toast.warning('Name and State are required');
      return;
    }
    setNewCustomerSaving(true);
    try {
      const {data} = await api.post('/customers',{...newCustomer,assigned_to:form.sales_person || undefined,status:'New'});
      setCustomers(prev=>[...prev,data]);
      setCustomerId(data.id);
      setForm(f=>({...f,address:f.address || data.address,site_location:f.site_location || data.project_site}));
      setNewCustomerOpen(false);
      setNewCustomer(blankNewCustomer);
      toast.success(`Customer ${data.name} added successfully!`);
    } catch (err) {
      toast.error('Failed to add customer');
    } finally { setNewCustomerSaving(false); }
  };

  const selected=customers.find(c=>c.id===customerId);
  return <>
    <PageHeader title={isEditing?'Edit Quotation':'Create Quotation'} subtitle={isEditing?'Update draft or sent quotation':'Quotations / New Quotation'} />
    <div className="quotation-layout">
      <div className="quote-main">
        <Card className="quote-form-card">
          <h3>Customer & Quotation Details</h3>
          <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:15}}>
            <div>
              <Field label="Customer Name" required>
                <div style={{display:'flex',gap:8}}>
                  <Select required style={{flex:1}} value={customerId} onChange={e=>setCustomerId(Number(e.target.value))}>
                    <option value={0} disabled>Select customer...</option>
                    {customers.map(c=><option key={c.id} value={c.id}>{c.name}</option>)}
                  </Select>
                  <button type="button" className="icon-btn" style={{background:'#edf4ff',borderColor:'#2468f2'}} title="Add New Customer" onClick={()=>setNewCustomerOpen(true)}><UserPlus2 size={17} style={{color:'#2468f2'}}/></button>
                </div>
                <small style={{color:'#60708a',marginTop:4,display:'block'}}>💡 Tip: Click the + icon to add a new customer</small>
              </Field>
              <Field label="Phone"><Input readOnly value={selected?.phone||''}/></Field>
              <Field label="Site Location"><Input value={form.site_location} onChange={e=>setForm({...form,site_location:e.target.value})}/></Field>
            </div>
            <div>
              <Field label="Sales Person" required><Select required value={form.sales_person} onChange={e=>setForm({...form,sales_person:e.target.value})}><option value="" disabled>Select sales person...</option><option>Arun Verma</option><option>Neha Kapoor</option><option>Rohit Singh</option></Select></Field>
              <Field label="Quotation Date" required><Input type="date" required value={form.quotation_date} onChange={e=>setForm({...form,quotation_date:e.target.value})}/></Field>
              <Field label="Validity" required><Select required value={form.validity_days || ''} onChange={e=>setForm({...form,validity_days:Number(e.target.value)})}><option value="" disabled>Select validity...</option><option value={15}>15 Days</option><option value={30}>30 Days</option><option value={45}>45 Days</option></Select></Field>
            </div>
          </div>
          <div style={{marginTop:15}}>
            <Field label="Address"><Input value={form.address} onChange={e=>setForm({...form,address:e.target.value})}/></Field>
          </div>
        </Card>

        <Card className="quote-items-card">
          <div style={{display:'flex',alignItems:'center',justifyContent:'space-between',marginBottom:15}}>
            <h3>Quotation Items</h3>
            <Button onClick={()=>setItems([...items,emptyItem()])} tone="secondary" style={{display:'flex',alignItems:'center',gap:6}}><Plus size={15}/> Add Item</Button>
          </div>
          <div className="table-wrap"><table className="data-table editable-table"><thead><tr><th style={{width:'40px'}}>#</th><th>Product</th><th>Dimensions</th><th style={{width:'80px'}}>Qty</th><th style={{width:'100px'}}>Rate/SFT</th><th style={{textAlign:'right',width:'120px'}}>Amount</th><th style={{width:'80px',textAlign:'center'}}>Actions</th></tr></thead><tbody>
            {items.map((row,i)=><>
              <tr key={`row-${i}`}>
                <td style={{textAlign:'center'}}>{i+1}</td>
                <td>
                  <select value={row.catalog_item_id || ''} onChange={e=>applyCatalog(i,Number(e.target.value))} style={{width:'100%'}}>
                    <option value="">Manual Entry</option>
                    {catalog.map(item=><option key={item.id} value={item.id}>{item.name}</option>)}
                  </select>
                  {row.category && <div style={{fontSize:'12px',color:'#60708a',marginTop:2}}>Category: {row.category}</div>}
                </td>
                <td>
                  <div style={{display:'flex',gap:8,alignItems:'center'}}>
                    <div><input type="number" placeholder="W" value={row.width_mm || ''} onChange={e=>update(i,'width_mm',e.target.value)} style={{width:60}}/></div>
                    <div style={{fontSize:'12px',color:'#60708a'}}>×</div>
                    <div><input type="number" placeholder="H" value={row.height_mm || ''} onChange={e=>update(i,'height_mm',e.target.value)} style={{width:60}}/></div>
                    <div style={{fontSize:'12px',color:'#60708a',whiteSpace:'nowrap'}}>({row.sft} SFT)</div>
                  </div>
                </td>
                <td><input type="number" value={row.quantity} onChange={e=>update(i,'quantity',e.target.value)} style={{width:'100%'}}/></td>
                <td><input type="number" placeholder="0" value={row.rate_per_sft || ''} onChange={e=>update(i,'rate_per_sft',e.target.value)} style={{width:'100%'}}/></td>
                <td className="amount" style={{textAlign:'right',fontWeight:600}}>{currency(row.amount,2)}</td>
                <td style={{textAlign:'center',display:'flex',gap:4,justifyContent:'center'}}>
                  <button type="button" className="icon-btn ghost" title="View specs" onClick={()=>{setSpecModalIndex(i);setSpecModalOpen(true);}} style={{padding:'4px 8px'}}><Eye size={14}/></button>
                  <button type="button" className="icon-btn ghost" title="Delete" onClick={()=>setItems(items.filter((_,x)=>x!==i))} style={{padding:'4px 8px',color:'#ef4444'}}><Trash2 size={14}/></button>
                </td>
              </tr>
            </>)}</tbody></table></div>
          <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',padding:'10px 12px',borderTop:'1px solid #e2e8f0',marginTop:10,fontSize:'13px'}}>
            <div><b>Total SFT: {totals.totalSft.toFixed(2)} | Subtotal: {currency(totals.subtotal,2)}</b></div>
          </div>
        </Card>

        <Card className="quote-notes"><small>Notes / Special Instructions (Optional)</small><textarea className="input" placeholder="Add any notes or special instructions..." value={form.notes} onChange={e=>setForm({...form,notes:e.target.value})}/></Card>
      </div>

      <aside>
        <Card className="quote-summary">
          <h3>Quote Summary</h3>
          <div className="summary-line"><span>Subtotal</span><b>{currency(totals.subtotal,2)}</b></div>
          <div className="summary-line"><span>Transport</span><Input type="number" placeholder="0" value={transport || ''} onChange={e=>setTransport(Number(e.target.value))} style={{width:100,height:31,textAlign:'right'}}/></div>
          <div className="summary-line"><span>Discount</span><Input type="number" placeholder="0" value={discount || ''} onChange={e=>setDiscount(Number(e.target.value))} style={{width:100,height:31,textAlign:'right',color:'#0eaf72'}}/></div>
          <hr style={{border:'none',borderTop:'1px solid #e2e8f0',margin:'10px 0'}}/>
          <div className="summary-line"><span>Taxable</span><b>{currency(totals.taxable,2)}</b></div>
          <div className="summary-line"><span>GST (18%)</span><b>{currency(totals.gst,2)}</b></div>
          <div className="summary-line total"><span>Grand Total</span><b style={{fontSize:'18px',color:'#2468f2'}}>{currency(totals.grand,2)}</b></div>
          <hr style={{border:'none',borderTop:'1px solid #e2e8f0',margin:'10px 0'}}/>
          <div className="payment-terms"><h4 style={{margin:'0 0 8px',fontSize:'13px'}}>Payment Terms</h4><div className="terms-circles"><div><div className="term-circle">50%</div><b style={{fontSize:'12px'}}>Advance</b><small>On Confirmation</small></div><div><div className="term-circle amber">40%</div><b style={{fontSize:'12px'}}>During Production</b><small>Before Dispatch</small></div><div><div className="term-circle blue">10%</div><b style={{fontSize:'12px'}}>On Installation</b><small>After Completion</small></div></div></div>
        </Card>
        <div className="quote-actionbar" style={{display:'flex',flexDirection:'column',gap:8}}>
          <Button onClick={()=>save(true)} disabled={saving}><Send size={15}/> Send Quotation</Button>
          <Button tone="secondary" onClick={()=>save(false)} disabled={saving}><Save size={15}/> {isEditing?'Save':'Save Draft'}</Button>
          <Button tone="secondary" onClick={()=>window.print()}><Download size={15}/> Print PDF</Button>
        </div>
      </aside>
    </div>

    <Modal open={specModalOpen && specModalIndex !== null} onClose={()=>setSpecModalOpen(false)} title={`Item ${(specModalIndex ?? 0) + 1} - Specifications`} width={640}>
      {specModalIndex !== null && <div className="form-grid three" style={{gap:20}}>
        <div>
          <small style={{color:'#60708a',fontSize:'11px',textTransform:'uppercase',fontWeight:600}}>Product</small>
          <input className="input" value={items[specModalIndex].category || ''} onChange={e=>update(specModalIndex,'category',e.target.value)} placeholder="Category / Type"/>
        </div>
        <div>
          <small style={{color:'#60708a',fontSize:'11px',textTransform:'uppercase',fontWeight:600}}>Style</small>
          <input className="input" value={items[specModalIndex].style || ''} onChange={e=>update(specModalIndex,'style',e.target.value)} placeholder="Style"/>
        </div>
        <div>
          <small style={{color:'#60708a',fontSize:'11px',textTransform:'uppercase',fontWeight:600}}>HSN Code</small>
          <input className="input" value={items[specModalIndex].hsn_code || ''} onChange={e=>update(specModalIndex,'hsn_code',e.target.value)} placeholder="HSN"/>
        </div>
        <div>
          <small style={{color:'#60708a',fontSize:'11px',textTransform:'uppercase',fontWeight:600}}>Profile</small>
          <input className="input" value={items[specModalIndex].profile || ''} onChange={e=>update(specModalIndex,'profile' as any,e.target.value)} placeholder="Material / Profile"/>
        </div>
        <div>
          <small style={{color:'#60708a',fontSize:'11px',textTransform:'uppercase',fontWeight:600}}>Color</small>
          <input className="input" value={items[specModalIndex].color || ''} onChange={e=>update(specModalIndex,'color' as any,e.target.value)} placeholder="Selected finish"/>
        </div>
        <div>
          <small style={{color:'#60708a',fontSize:'11px',textTransform:'uppercase',fontWeight:600}}>Track</small>
          <input className="input" value={items[specModalIndex].track || ''} onChange={e=>update(specModalIndex,'track' as any,e.target.value)} placeholder="Track / Opening"/>
        </div>
        <div>
          <small style={{color:'#60708a',fontSize:'11px',textTransform:'uppercase',fontWeight:600}}>Glass</small>
          <input className="input" value={items[specModalIndex].glass || ''} onChange={e=>update(specModalIndex,'glass' as any,e.target.value)} placeholder="Glass spec"/>
        </div>
        <div>
          <small style={{color:'#60708a',fontSize:'11px',textTransform:'uppercase',fontWeight:600}}>Glass Color</small>
          <input className="input" value={items[specModalIndex].glass_color || ''} onChange={e=>update(specModalIndex,'glass_color' as any,e.target.value)} placeholder="Tint"/>
        </div>
        <div>
          <small style={{color:'#60708a',fontSize:'11px',textTransform:'uppercase',fontWeight:600}}>Hardware</small>
          <input className="input" value={items[specModalIndex].hardware || ''} onChange={e=>update(specModalIndex,'hardware' as any,e.target.value)} placeholder="Hardware set"/>
        </div>
        <div>
          <small style={{color:'#60708a',fontSize:'11px',textTransform:'uppercase',fontWeight:600}}>Reinforcement</small>
          <input className="input" value={items[specModalIndex].reinforcement || ''} onChange={e=>update(specModalIndex,'reinforcement' as any,e.target.value)} placeholder="Internal support"/>
        </div>
        <div>
          <small style={{color:'#60708a',fontSize:'11px',textTransform:'uppercase',fontWeight:600}}>Mesh</small>
          <input className="input" value={items[specModalIndex].mesh || ''} onChange={e=>update(specModalIndex,'mesh' as any,e.target.value)} placeholder="Mesh option"/>
        </div>
        <div>
          <small style={{color:'#60708a',fontSize:'11px',textTransform:'uppercase',fontWeight:600}}>Location</small>
          <input className="input" value={items[specModalIndex].location || ''} onChange={e=>update(specModalIndex,'location',e.target.value)} placeholder="Warehouse location"/>
        </div>
      </div>}
      <div className="form-actions" style={{marginTop:20}}>
        <Button tone="secondary" onClick={()=>setSpecModalOpen(false)}>Done</Button>
      </div>
    </Modal>

    <Modal open={newCustomerOpen} onClose={()=>setNewCustomerOpen(false)} title="✨ Add New Customer" width={640}>
      <form onSubmit={submitNewCustomer}>
        <div className="form-grid">
          <Field label="Customer Name" required><Input required autoFocus value={newCustomer.name} onChange={e=>setNewCustomer({...newCustomer,name:e.target.value})} placeholder="e.g., Arun's Home Furnish"/></Field>
          <Field label="State" required><Select required value={newCustomer.state} onChange={e=>setNewCustomer({...newCustomer,state:e.target.value})}><option value="">Select state...</option>{INDIAN_STATES.map(s=><option key={s}>{s}</option>)}</Select></Field>
          <Field label="Phone"><Input value={newCustomer.phone} onChange={e=>setNewCustomer({...newCustomer,phone:e.target.value})} placeholder="Phone number"/></Field>
          <Field label="Email"><Input type="email" value={newCustomer.email} onChange={e=>setNewCustomer({...newCustomer,email:e.target.value})} placeholder="email@example.com"/></Field>
          <Field label="Project / Site"><Input value={newCustomer.project_site} onChange={e=>setNewCustomer({...newCustomer,project_site:e.target.value})} placeholder="e.g., Residential / Commercial"/></Field>
          <Field label="GST Number"><Input value={newCustomer.gst_number} onChange={e=>setNewCustomer({...newCustomer,gst_number:e.target.value})} placeholder="27AAJPA1234A1Z5"/></Field>
          <div style={{gridColumn:'span 2'}}><Field label="Address"><textarea className="input" value={newCustomer.address} onChange={e=>setNewCustomer({...newCustomer,address:e.target.value})} placeholder="Full address..."/></Field></div>
        </div>
        <div style={{background:'#f7fbff',padding:12,borderRadius:8,margin:'15px 0',fontSize:'12px',color:'#60708a'}}>
          💡 <b>After saving</b>, this customer will be automatically selected and you can continue creating the quotation.
        </div>
        <div className="form-actions"><Button type="button" tone="secondary" onClick={()=>setNewCustomerOpen(false)}>Cancel</Button><Button type="submit" disabled={newCustomerSaving}><UserPlus2 size={14}/> {newCustomerSaving?'Saving...':'Add & Select'}</Button></div>
      </form>
    </Modal>
  </>;
}
