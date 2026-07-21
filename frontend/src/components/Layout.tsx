import { useEffect, useMemo, useRef, useState } from 'react';
import {
  Bell,
  BookOpen,
  Boxes,
  Building2,
  CalendarClock,
  CalendarDays,
  ChevronDown,
  ClipboardList,
  Clock,
  FileArchive,
  FileMinus,
  FilePlus2,
  FileText,
  FolderInput,
  HandCoins,
  Landmark,
  LayoutDashboard,
  Menu,
  PackageSearch,
  Percent,
  Receipt,
  ReceiptText,
  Scale,
  ScrollText,
  Search,
  Settings,
  TrendingUp,
  Truck,
  UsersRound,
  Waves,
} from 'lucide-react';
import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import api from '../api';
import { BusinessSettings, Customer, Invoice, Quotation } from '../types';

const navigation = [
  ['Dashboard', '/', LayoutDashboard],
  ['Customers', '/customers', UsersRound],
  ['Quotations', '/quotations', FileText],
  ['Invoices', '/invoices', ReceiptText],
  ['Credit Notes', '/credit-notes', FileMinus],
  ['Debit Notes', '/debit-notes', FilePlus2],
  ['Payments', '/payments', HandCoins],
  ['Vendors', '/vendors', Truck],
  ['Purchase Bills', '/purchase-bills', ClipboardList],
  ['Expenses', '/expenses', Receipt],
  ['Stock Items', '/stock-items', PackageSearch],
  ['Fixed Assets', '/fixed-assets', Building2],
  ['Chart of Accounts', '/accounts', BookOpen],
  ['Journal', '/journal', ClipboardList],
  ['Trial Balance', '/trial-balance', Scale],
  ['Financial Years', '/financial-years', CalendarClock],
  ['GST Reports', '/gst-reports', Percent],
  ['Profit & Loss', '/profit-and-loss', ScrollText],
  ['Balance Sheet', '/balance-sheet', Landmark],
  ['Cash Flow', '/cash-flow', Waves],
  ['AP Aging', '/ap-aging', Clock],
  ['Tally Export', '/tally-export', FileArchive],
  ['Opening Balances', '/opening-balances', FolderInput],
  ['Follow-ups', '/followups', Bell],
  ['Catalog', '/catalog', Boxes],
  ['Reports', '/reports', TrendingUp],
  ['Settings', '/settings', Settings],
] as const;

type SearchResults = { customers: Customer[]; invoices: Invoice[]; quotations: Quotation[] };
const emptyResults: SearchResults = { customers: [], invoices: [], quotations: [] };

export default function Layout() {
  const navigate = useNavigate();
  const [business, setBusiness] = useState<BusinessSettings | null>(null);
  const [overdueCount, setOverdueCount] = useState(0);
  const [allInvoices, setAllInvoices] = useState<Invoice[]>([]);
  const [allQuotations, setAllQuotations] = useState<Quotation[]>([]);
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResults>(emptyResults);
  const [searchOpen, setSearchOpen] = useState(false);
  const searchInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    api.get('/business-settings').then(r => setBusiness(r.data));
    api.get('/dashboard').then(r => setOverdueCount(r.data.metrics.overdue_invoice_count || 0));
    api.get('/invoices').then(r => setAllInvoices(r.data));
    api.get('/quotations').then(r => setAllQuotations(r.data));
  }, []);

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') { e.preventDefault(); searchInputRef.current?.focus(); }
      if (e.key === 'Escape') { setSearchOpen(false); searchInputRef.current?.blur(); }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, []);

  useEffect(() => {
    const term = query.trim();
    if (term.length < 2) { setResults(emptyResults); return; }
    const q = term.toLowerCase();
    const handle = setTimeout(() => {
      api.get('/customers', { params: { search: term } }).then(r => {
        setResults({
          customers: r.data.slice(0, 4),
          invoices: allInvoices.filter(i => i.number.toLowerCase().includes(q) || i.customer.name.toLowerCase().includes(q)).slice(0, 4),
          quotations: allQuotations.filter(qu => qu.number.toLowerCase().includes(q) || qu.customer.name.toLowerCase().includes(q)).slice(0, 4),
        });
      });
    }, 250);
    return () => clearTimeout(handle);
  }, [query, allInvoices, allQuotations]);

  const hasResults = results.customers.length + results.invoices.length + results.quotations.length > 0;

  const goTo = (path: string) => { navigate(path); setQuery(''); setResults(emptyResults); setSearchOpen(false); searchInputRef.current?.blur(); };

  const today = useMemo(() => new Date().toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' }), []);
  const companyName = business?.company_name || 'Your Business';
  const companyTagline = business?.tagline || '';

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark"><span /><span /></div>
          <div><strong>UPVC Pro</strong><small>Windows. Doors. Trust.</small></div>
        </div>
        <nav className="sidebar-nav">
          {navigation.map(([label, path, Icon]) => (
            <NavLink key={path} to={path} end={path === '/'} className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
              <Icon size={20} strokeWidth={1.8} />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>
        <div className="company-card">
          <div className="window-thumb">
            <i /><i /><i />
          </div>
          <div><b>{companyName}</b><small>{companyTagline}</small></div>
        </div>
      </aside>

      <section className="main-shell">
        <header className="topbar">
          <button className="icon-btn ghost"><Menu size={21} /></button>
          <div className="global-search" style={{ position: 'relative' }}>
            <Search size={18} />
            <input
              ref={searchInputRef}
              placeholder="Search customers, quotations, invoices..."
              value={query}
              onChange={e => setQuery(e.target.value)}
              onFocus={() => setSearchOpen(true)}
              onBlur={() => setTimeout(() => setSearchOpen(false), 150)}
            />
            <kbd>Ctrl + K</kbd>
            {searchOpen && query.trim().length >= 2 && (
              <div className="search-dropdown" style={{ position: 'absolute', top: '48px', left: 0, right: 0, background: '#fff', border: '1px solid var(--border)', borderRadius: 9, boxShadow: '0 12px 28px rgba(17,32,64,.14)', maxHeight: 360, overflowY: 'auto', zIndex: 30 }}>
                {!hasResults && <div style={{ padding: '14px 16px', color: '#7a8699', fontSize: 13 }}>No matches for "{query.trim()}"</div>}
                {results.customers.length > 0 && <div>
                  <div style={{ padding: '8px 16px 4px', fontSize: 11, textTransform: 'uppercase', letterSpacing: '.05em', color: '#8a95a5' }}>Customers</div>
                  {results.customers.map(c => <button key={c.id} onMouseDown={() => goTo(`/customers?q=${encodeURIComponent(c.name)}`)} className="search-result-row">
                    <b>{c.name}</b><small>{c.phone}</small>
                  </button>)}
                </div>}
                {results.invoices.length > 0 && <div>
                  <div style={{ padding: '8px 16px 4px', fontSize: 11, textTransform: 'uppercase', letterSpacing: '.05em', color: '#8a95a5' }}>Invoices</div>
                  {results.invoices.map(i => <button key={i.id} onMouseDown={() => goTo(`/invoices/${i.id}`)} className="search-result-row">
                    <b>{i.number}</b><small>{i.customer.name}</small>
                  </button>)}
                </div>}
                {results.quotations.length > 0 && <div>
                  <div style={{ padding: '8px 16px 4px', fontSize: 11, textTransform: 'uppercase', letterSpacing: '.05em', color: '#8a95a5' }}>Quotations</div>
                  {results.quotations.map(q => <button key={q.id} onMouseDown={() => goTo(`/quotations/${q.id}`)} className="search-result-row">
                    <b>{q.number}</b><small>{q.customer.name}</small>
                  </button>)}
                </div>}
              </div>
            )}
          </div>
          <div className="topbar-spacer" />
          <div className="date-range"><CalendarDays size={18} /><span>{today}</span></div>
          <button className="icon-btn notification" title={`${overdueCount} overdue invoice${overdueCount === 1 ? '' : 's'}`} onClick={() => navigate('/invoices')}>
            <Bell size={19} />
            {overdueCount > 0 && <em>{overdueCount > 9 ? '9+' : overdueCount}</em>}
          </button>
        </header>
        <main className="page-content"><Outlet /></main>
        <footer className="footer"><span>&copy; {new Date().getFullYear()} {companyName}. All rights reserved.</span><span>Privacy Policy&nbsp;&nbsp;&nbsp;&nbsp; Terms of Service</span></footer>
      </section>
    </div>
  );
}
