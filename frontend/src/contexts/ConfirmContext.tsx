import { createContext, useCallback, useContext, useRef, useState, ReactNode } from 'react';
import { ConfirmDialog } from '../components/ConfirmDialog';

interface ConfirmOptions {
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  isDangerous?: boolean;
}

type ConfirmFn = (options: ConfirmOptions) => Promise<boolean>;

const ConfirmContext = createContext<ConfirmFn | undefined>(undefined);

/**
 * Promise-based replacement for window.confirm, so destructive actions use the
 * app's own dialog instead of the browser's. Call sites keep the same shape:
 *   if (!(await confirm({ ... }))) return;
 */
export function ConfirmProvider({ children }: { children: ReactNode }) {
  const [options, setOptions] = useState<ConfirmOptions | null>(null);
  const resolver = useRef<((value: boolean) => void) | null>(null);

  const confirm = useCallback<ConfirmFn>(opts => {
    setOptions(opts);
    return new Promise<boolean>(resolve => { resolver.current = resolve; });
  }, []);

  const settle = (result: boolean) => {
    resolver.current?.(result);
    resolver.current = null;
    setOptions(null);
  };

  return (
    <ConfirmContext.Provider value={confirm}>
      {children}
      <ConfirmDialog
        open={options !== null}
        title={options?.title ?? ''}
        message={options?.message ?? ''}
        confirmLabel={options?.confirmLabel}
        cancelLabel={options?.cancelLabel}
        isDangerous={options?.isDangerous}
        onConfirm={() => settle(true)}
        onCancel={() => settle(false)}
      />
    </ConfirmContext.Provider>
  );
}

export function useConfirm(): ConfirmFn {
  const context = useContext(ConfirmContext);
  if (undefined === context) {
    throw new Error('useConfirm must be used within ConfirmProvider');
  }
  return context;
}
