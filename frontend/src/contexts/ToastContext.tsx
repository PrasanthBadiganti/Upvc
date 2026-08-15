import { createContext, useContext, ReactNode } from 'react';
import { useToast } from '../hooks/useToast';
import { ToastContainer } from '../components/Toast';

interface ToastContextType {
  success: (message: string, duration?: number) => string;
  error: (message: string, duration?: number) => string;
  info: (message: string, duration?: number) => string;
  warning: (message: string, duration?: number) => string;
}

const ToastContext = createContext<ToastContextType | undefined>(undefined);

export function ToastProvider({ children }: { children: ReactNode }) {
  const { toasts, dismiss, success, error, info, warning } = useToast();

  return (
    <ToastContext.Provider value={{ success, error, info, warning }}>
      <ToastContainer toasts={toasts} onDismiss={dismiss} />
      {children}
    </ToastContext.Provider>
  );
}

export function useToastContext() {
  const context = useContext(ToastContext);
  if (undefined === context) {
    throw new Error('useToastContext must be used within ToastProvider');
  }
  return context;
}
