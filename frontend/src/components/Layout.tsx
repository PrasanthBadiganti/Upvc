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
  Wallet,
  Waves,
} from 'lucide-react';
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom';
import api from '../api';
import { BusinessSettings, Customer, Invoice, Quotation } from '../types';

const navGroups = [
  { key: 'top', label: null, items: [
    ['Dashboard', '/', LayoutDashboard],
  ] },
  { key: 'sales', label: 'Sales & CRM', items: [
    ['Customers', '/customers', UsersRound],
    ['Quotations', '/quotations', FileText],
    ['Invoices', '/invoices', ReceiptText],
    ['Credit Notes', '/credit-notes', FileMinus],
    ['Debit Notes', '/debit-notes', FilePlus2],
    ['Payments', '/payments', HandCoins],
    ['Follow-ups', '/followups', Bell],
    ['Catalog', '/catalog', Boxes],
  ] },
  { key: 'purchasing', label: 'Purchasing & Inventory', items: [
    ['Vendors', '/vendors', Truck],
    ['Purchase Bills', '/purchase-bills', ClipboardList],
    ['Expenses', '/expenses', Receipt],
    ['Stock Items', '/stock-items', PackageSearch],
  ] },
  { key: 'accounting', label: 'Accounting', items: [
    ['Bank Accounts', '/bank-accounts', Wallet],
    ['Chart of Accounts', '/accounts', BookOpen],
    ['Journal', '/journal', ClipboardList],
    ['Trial Balance', '/trial-balance', Scale],
    ['Fixed Assets', '/fixed-assets', Building2],
    ['Financial Years', '/financial-years', CalendarClock],
  ] },
  { key: 'reports', label: 'Reports & Filing', items: [
    ['GST Reports', '/gst-reports', Percent],
    ['Profit & Loss', '/profit-and-loss', ScrollText],
    ['Balance Sheet', '/balance-sheet', Landmark],
    ['Cash Flow', '/cash-flow', Waves],
    ['AP Aging', '/ap-aging', Clock],
    ['Reports', '/reports', TrendingUp],
  ] },
  { key: 'data', label: 'Data Tools', items: [
    ['Tally Export', '/tally-export', FileArchive],
    ['Opening Balances', '/opening-balances', FolderInput],
  ] },
  { key: 'bottom', label: null, items: [
    ['Settings', '/settings', Settings],
  ] },
] as const;

const DEFAULT_EXPANDED_GROUPS = ['sales', 'purchasing'];
const SIDEBAR_STORAGE_KEY = 'upvc-sidebar-expanded-groups';

function renderNavItem([label, path, Icon]: readonly [string, string, typeof LayoutDashboard]) {
  return (
    <NavLink key={path} to={path} end={path === '/'} className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
      <Icon size={18} strokeWidth={1.8} />
      <span>{label}</span>
    </NavLink>
  );
}

function groupKeyForPath(pathname: string): string | null {
  for (const group of navGroups) {
    if (group.items.some(([, path]) => path === '/' ? pathname === '/' : pathname.startsWith(path))) return group.key;
  }
  return null;
}

type SearchResults = { customers: Customer[]; invoices: Invoice[]; quotations: Quotation[] };
const emptyResults: SearchResults = { customers: [], invoices: [], quotations: [] };

export default function Layout() {
  const navigate = useNavigate();
  const location = useLocation();
  const [business, setBusiness] = useState<BusinessSettings | null>(null);
  const [overdueCount, setOverdueCount] = useState(0);
  const [allInvoices, setAllInvoices] = useState<Invoice[]>([]);
  const [allQuotations, setAllQuotations] = useState<Quotation[]>([]);
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResults>(emptyResults);
  const [searchOpen, setSearchOpen] = useState(false);
  const searchInputRef = useRef<HTMLInputElement>(null);
  const [expandedGroups, setExpandedGroups] = useState<string[]>(() => {
    try {
      const saved = localStorage.getItem(SIDEBAR_STORAGE_KEY);
      return saved ? JSON.parse(saved) : DEFAULT_EXPANDED_GROUPS;
    } catch { return DEFAULT_EXPANDED_GROUPS; }
  });

  useEffect(() => {
    const activeGroup = groupKeyForPath(location.pathname);
    if (activeGroup && !expandedGroups.includes(activeGroup)) {
      setExpandedGroups(prev => [...prev, activeGroup]);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [location.pathname]);

  const toggleGroup = (key: string) => {
    setExpandedGroups(prev => {
      const next = prev.includes(key) ? prev.filter(k => k !== key) : [...prev, key];
      localStorage.setItem(SIDEBAR_STORAGE_KEY, JSON.stringify(next));
      return next;
    });
  };

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
          {business?.logo_path ? (
            <img src={`${business.logo_path}?v=${encodeURIComponent(business.updated_at)}`} alt="Business logo" className="brand-logo" />
          ) : (
            <>
              <div className="brand-mark"><span /><span /></div>
              <div><strong>{business?.logo_text || 'UPVC'}</strong></div>
            </>
          )}
        </div>
        <nav className="sidebar-nav">
          {navGroups.map(group => {
            if (!group.label) {
              return group.items.map(item => renderNavItem(item));
            }
            const expanded = expandedGroups.includes(group.key);
            return (
              <div className="nav-group" key={group.key}>
                <button type="button" className="nav-group-header" onClick={() => toggleGroup(group.key)}>
                  <span>{group.label}</span>
                  <ChevronDown size={15} style={{ transform: expanded ? 'none' : 'rotate(-90deg)', transition: 'transform .15s' }} />
                </button>
                {expanded && group.items.map(item => renderNavItem(item))}
              </div>
            );
          })}
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
                {!hasResults && <div style={{ padding: '14px 16px', color: '#7a8699', fontSize: 14 }}>No matches for "{query.trim()}"</div>}
                {results.customers.length > 0 && <div>
                  <div style={{ padding: '8px 16px 4px', fontSize: 13, textTransform: 'uppercase', letterSpacing: '.05em', color: '#8a95a5' }}>Customers</div>
                  {results.customers.map(c => <button key={c.id} onMouseDown={() => goTo(`/customers?q=${encodeURIComponent(c.name)}`)} className="search-result-row">
                    <b>{c.name}</b><small>{c.phone}</small>
                  </button>)}
                </div>}
                {results.invoices.length > 0 && <div>
                  <div style={{ padding: '8px 16px 4px', fontSize: 13, textTransform: 'uppercase', letterSpacing: '.05em', color: '#8a95a5' }}>Invoices</div>
                  {results.invoices.map(i => <button key={i.id} onMouseDown={() => goTo(`/invoices/${i.id}`)} className="search-result-row">
                    <b>{i.number}</b><small>{i.customer.name}</small>
                  </button>)}
                </div>}
                {results.quotations.length > 0 && <div>
                  <div style={{ padding: '8px 16px 4px', fontSize: 13, textTransform: 'uppercase', letterSpacing: '.05em', color: '#8a95a5' }}>Quotations</div>
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
