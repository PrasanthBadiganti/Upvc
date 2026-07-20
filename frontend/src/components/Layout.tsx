import {
  Bell,
  BookOpen,
  Boxes,
  CalendarDays,
  ChevronDown,
  ClipboardList,
  FileMinus,
  FilePlus2,
  FileText,
  Gauge,
  HandCoins,
  LayoutDashboard,
  Menu,
  Receipt,
  ReceiptText,
  Scale,
  Search,
  Settings,
  TrendingUp,
  Truck,
  UserRound,
  UsersRound,
} from 'lucide-react';
import { NavLink, Outlet } from 'react-router-dom';

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
  ['Chart of Accounts', '/accounts', BookOpen],
  ['Journal', '/journal', ClipboardList],
  ['Trial Balance', '/trial-balance', Scale],
  ['Follow-ups', '/followups', Bell],
  ['Catalog', '/catalog', Boxes],
  ['Reports', '/reports', TrendingUp],
  ['Settings', '/settings', Settings],
] as const;

export default function Layout() {
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
          <div><b>Crystal Frames Pvt. Ltd.</b><small>UPVC Doors | Windows | Glass</small></div>
          <ChevronDown size={15} className="company-chevron" />
        </div>
      </aside>

      <section className="main-shell">
        <header className="topbar">
          <button className="icon-btn ghost"><Menu size={21} /></button>
          <div className="global-search"><Search size={18} /><input placeholder="Search customers, quotations, invoices..." /><kbd>Ctrl + K</kbd></div>
          <div className="topbar-spacer" />
          <button className="date-range"><CalendarDays size={18} /><span>01 May 2025 - 31 May 2025</span><ChevronDown size={16} /></button>
          <button className="icon-btn notification"><Bell size={19} /><em>5</em></button>
          <div className="profile-block">
            <div className="avatar">AV</div>
            <div><b>Arun Verma</b><small>Admin</small></div>
            <ChevronDown size={15} />
          </div>
        </header>
        <main className="page-content"><Outlet /></main>
        <footer className="footer"><span>(c) 2025 Crystal Frames Pvt. Ltd. All rights reserved.</span><span>Privacy Policy&nbsp;&nbsp;&nbsp;&nbsp; Terms of Service</span></footer>
      </section>
    </div>
  );
}
