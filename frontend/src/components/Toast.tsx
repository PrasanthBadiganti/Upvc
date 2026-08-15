import { X, CheckCircle, AlertCircle, Info, AlertTriangle } from 'lucide-react';
import { Toast as ToastType } from '../hooks/useToast';

interface ToastContainerProps {
  toasts: ToastType[];
  onDismiss: (id: string) => void;
}

export function ToastContainer({ toasts, onDismiss }: ToastContainerProps) {
  if (toasts.length === 0) return null;

  return (
    <div style={{ position: 'fixed', top: 20, right: 20, zIndex: 200, display: 'flex', flexDirection: 'column', gap: 10 }}>
      {toasts.map(toast => <Toast key={toast.id} toast={toast} onDismiss={onDismiss} />)}
    </div>
  );
}

interface ToastProps {
  toast: ToastType;
  onDismiss: (id: string) => void;
}

function Toast({ toast, onDismiss }: ToastProps) {
  const colors = {
    success: { bg: '#f0fdf4', text: '#15803d', border: '#22c55e', icon: '#22c55e' },
    error: { bg: '#fef2f2', text: '#991b1b', border: '#ef4444', icon: '#ef4444' },
    info: { bg: '#f0f9ff', text: '#0c4a6e', border: '#0ea5e9', icon: '#0ea5e9' },
    warning: { bg: '#fffbeb', text: '#92400e', border: '#f59e0b', icon: '#f59e0b' },
  };

  const color = colors[toast.type];
  const Icon = toast.type === 'success' ? CheckCircle : toast.type === 'error' ? AlertCircle : toast.type === 'warning' ? AlertTriangle : Info;

  return (
    <div
      style={{
        background: color.bg,
        border: `1px solid ${color.border}`,
        borderRadius: 8,
        padding: '12px 16px',
        display: 'flex',
        gap: 12,
        alignItems: 'center',
        minWidth: 300,
        maxWidth: 400,
        boxShadow: '0 4px 12px rgba(0, 0, 0, 0.1)',
      }}
    >
      <Icon size={20} style={{ color: color.icon, flex: '0 0 auto' }} />
      <span style={{ color: color.text, fontSize: 14, flex: 1, fontWeight: 500 }}>{toast.message}</span>
      <button
        onClick={() => onDismiss(toast.id)}
        style={{
          background: 'transparent',
          border: 'none',
          cursor: 'pointer',
          padding: 0,
          color: color.text,
          display: 'flex',
          alignItems: 'center',
          flex: '0 0 auto',
        }}
      >
        <X size={18} />
      </button>
    </div>
  );
}
