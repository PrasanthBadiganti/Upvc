import { LucideIcon } from 'lucide-react';

export default function MetricCard({ label, value, change, icon: Icon, tone = 'blue' }: { label: string; value: string | number; change?: string; icon: LucideIcon; tone?: string }) {
  return (
    <div className="metric-card">
      <div className={`metric-icon ${tone}`}><Icon size={23} /></div>
      <div className="metric-copy"><small>{label}</small><strong>{value}</strong>{change && <span className={change.trim().startsWith('-') ? 'negative' : 'positive'}>{change}</span>}</div>
    </div>
  );
}
