import { CSSProperties, ReactNode, useState } from 'react';
import { ChevronRight, X } from 'lucide-react';

export function Card({ children, className = '', ...props }: React.HTMLAttributes<HTMLElement> & { children: ReactNode }) {
  return <section className={`card ${className}`} {...props}>{children}</section>;
}

/**
 * `toolbar` (search, filters, refresh) sits on the same line as the title and
 * the primary action, so a list page spends one row on its chrome instead of
 * two. Pages with no toolbar are unaffected.
 */
export function PageHeader({ title, subtitle, toolbar, action }: {
  title: string; subtitle?: string; toolbar?: ReactNode; action?: ReactNode;
}) {
  return (
    <div className={`page-header${toolbar ? ' with-toolbar' : ''}`}>
      <div className="page-header-titles"><h1>{title}</h1>{subtitle && <p>{subtitle}</p>}</div>
      {toolbar && <div className="page-header-toolbar">{toolbar}</div>}
      {action}
    </div>
  );
}

export function Badge({ children, tone = 'blue' }: { children: ReactNode; tone?: string }) {
  return <span className={`badge ${tone}`}>{children}</span>;
}

export function Button({ children, tone = 'primary', className = '', ...props }: React.ButtonHTMLAttributes<HTMLButtonElement> & { tone?: 'primary' | 'secondary' | 'danger' | 'success' | 'ghost' }) {
  return <button className={`button ${tone} ${className}`} {...props}>{children}</button>;
}

export function Input(props: React.InputHTMLAttributes<HTMLInputElement>) {
  return <input className="input" {...props} />;
}

export function Select(props: React.SelectHTMLAttributes<HTMLSelectElement>) {
  return <select className="input select" {...props} />;
}

export function Field({ label, required, children }: { label: string; required?: boolean; children: ReactNode }) {
  return <label className="field"><span>{label}{required && <i>*</i>}</span>{children}</label>;
}

export function Modal({ open, title, children, onClose, width = 640 }: { open: boolean; title: string; children: ReactNode; onClose: () => void; width?: number }) {
  if (!open) return null;
  return (
    <div className="modal-backdrop" onMouseDown={onClose}>
      <div className="modal" style={{ width }} onMouseDown={e => e.stopPropagation()}>
        <div className="modal-head"><h3>{title}</h3><button className="icon-btn ghost" onClick={onClose}><X size={19} /></button></div>
        <div className="modal-body">{children}</div>
      </div>
    </div>
  );
}

/**
 * A titled section that folds away, for pages that stack several long tables.
 * The row count stays on the header so you can tell whether a collapsed section
 * is worth opening, and the body caps its own height and scrolls internally -
 * otherwise one 300-row table pushes every section below it off the screen.
 */
export function CollapsibleSection({ title, count, actions, defaultOpen = false, bodyHeight = 320, children }: {
  title: string;
  count?: number;
  actions?: ReactNode;
  defaultOpen?: boolean;
  bodyHeight?: number;
  children: ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <Card className="collapsible-card">
      <div className="card-head collapsible-head">
        <button type="button" className="collapsible-toggle" onClick={() => setOpen(o => !o)} aria-expanded={open}>
          <ChevronRight size={15} className={`chev${open ? ' open' : ''}`} />
          <h3>{title}</h3>
          {count !== undefined && <span className="count-pill">{count}</span>}
        </button>
        {actions}
      </div>
      {open && (
        <div className="collapsible-body" style={{ '--collapse-h': `${bodyHeight}px` } as CSSProperties}>
          {children}
        </div>
      )}
    </Card>
  );
}

export function Empty({ message = 'No data found' }: { message?: string }) {
  return <div className="empty-state">{message}</div>;
}

export function Loading() {
  return <div className="loading"><span /><span /><span /></div>;
}
