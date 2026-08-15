import { useEffect } from 'react';

interface KeyboardShortcutConfig {
  key: string; // e.g., 'S', 'Enter'
  ctrl?: boolean;
  shift?: boolean;
  alt?: boolean;
  meta?: boolean;
  onPress: () => void;
  disabled?: boolean;
}

export const useKeyboardShortcut = (configs: KeyboardShortcutConfig | KeyboardShortcutConfig[]) => {
  useEffect(() => {
    const configArray = Array.isArray(configs) ? configs : [configs];

    const handleKeyDown = (event: KeyboardEvent) => {
      for (const config of configArray) {
        if (config.disabled) continue;

        const keyMatches = event.key.toUpperCase() === config.key.toUpperCase();
        const ctrlMatches = (config.ctrl || false) === (event.ctrlKey || event.metaKey);
        const shiftMatches = (config.shift || false) === event.shiftKey;
        const altMatches = (config.alt || false) === event.altKey;

        if (keyMatches && ctrlMatches && shiftMatches && altMatches) {
          event.preventDefault();
          config.onPress();
          break;
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [configs]);
};

// Common shortcuts
export const SHORTCUTS = {
  SAVE: { key: 'S', ctrl: true },
  ENTER: { key: 'Enter', ctrl: true },
  ESC: { key: 'Escape' },
  PRINT: { key: 'P', ctrl: true },
  NEW: { key: 'N', ctrl: true },
  DELETE: { key: 'Delete' },
};
