import { AlertTriangle } from 'lucide-react';
import { Button } from './UI';

interface ConfirmDialogProps {
  open: boolean;
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  isDangerous?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
  isLoading?: boolean;
}

export function ConfirmDialog({
  open,
  title,
  message,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  isDangerous = false,
  onConfirm,
  onCancel,
  isLoading = false,
}: ConfirmDialogProps) {
  if (!open) return null;

  return (
    <div className="modal-backdrop" onMouseDown={onCancel}>
      <div className="modal" style={{ width: 400 }} onMouseDown={e => e.stopPropagation()}>
        <div className="modal-head">
          <h3 style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            {isDangerous && <AlertTriangle size={20} style={{ color: '#ef4444' }} />}
            {title}
          </h3>
          <button className="icon-btn ghost" onClick={onCancel}>✕</button>
        </div>
        <div className="modal-body">
          <p style={{ color: '#60708a', marginBottom: 20 }}>{message}</p>
          <div className="form-actions">
            <Button type="button" tone="secondary" onClick={onCancel} disabled={isLoading}>
              {cancelLabel}
            </Button>
            <Button
              type="button"
              tone={isDangerous ? 'danger' : 'primary'}
              onClick={onConfirm}
              disabled={isLoading}
            >
              {isLoading ? 'Loading...' : confirmLabel}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
