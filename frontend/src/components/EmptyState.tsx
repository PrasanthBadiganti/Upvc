import { ReactNode } from 'react';
import { Button } from './UI';

interface EmptyStateProps {
  icon?: ReactNode;
  title: string;
  description: string;
  action?: {
    label: string;
    onClick: () => void;
  };
  hint?: string;
}

export function EmptyState({ icon, title, description, action, hint }: EmptyStateProps) {
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '60px 40px',
        textAlign: 'center',
        minHeight: 300,
      }}
    >
      {icon && <div style={{ marginBottom: 20, fontSize: 48 }}>{icon}</div>}
      <h3 style={{ fontSize: 18, marginBottom: 8, color: '#1c2d4e', fontWeight: 600 }}>{title}</h3>
      <p style={{ fontSize: 14, color: '#60708a', marginBottom: 20, maxWidth: 400 }}>{description}</p>
      {hint && <small style={{ color: '#8a95a5', fontSize: 13, marginBottom: 20 }}>{hint}</small>}
      {action && (
        <Button onClick={action.onClick} style={{ marginTop: 10 }}>
          {action.label}
        </Button>
      )}
    </div>
  );
}
