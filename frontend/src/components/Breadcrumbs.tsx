import { ChevronRight } from 'lucide-react';
import { Link } from 'react-router-dom';

export interface BreadcrumbItem {
  label: string;
  path?: string;
}

interface BreadcrumbsProps {
  items: BreadcrumbItem[];
}

export function Breadcrumbs({ items }: BreadcrumbsProps) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12, fontSize: 12.5, color: '#60708a' }}>
      {items.map((item, index) => (
        <div key={index} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {index > 0 && <ChevronRight size={14} style={{ color: '#cbd5e1' }} />}
          {item.path ? (
            <Link to={item.path} style={{ color: '#2468f2', textDecoration: 'none', cursor: 'pointer' }}>
              {item.label}
            </Link>
          ) : (
            <span style={{ color: '#60708a' }}>{item.label}</span>
          )}
        </div>
      ))}
    </div>
  );
}
