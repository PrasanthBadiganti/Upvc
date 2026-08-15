import { useState, useRef, useEffect } from 'react';
import { Search, ChevronDown, X } from 'lucide-react';

interface Option {
  value: string | number;
  label: string;
}

interface SearchableSelectProps {
  options: Option[];
  value: string | number | null;
  onChange: (value: string | number | null) => void;
  placeholder?: string;
  required?: boolean;
  style?: React.CSSProperties;
}

export function SearchableSelect({
  options,
  value,
  onChange,
  placeholder = 'Search and select...',
  required = false,
  style = {},
}: SearchableSelectProps) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState('');
  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const selectedOption = options.find(opt => opt.value === value);
  const filtered = options.filter(opt =>
    opt.label.toLowerCase().includes(search.toLowerCase())
  );

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    }

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  useEffect(() => {
    if (open && inputRef.current) {
      inputRef.current.focus();
    }
  }, [open]);

  return (
    <div ref={containerRef} style={{ position: 'relative', ...style }}>
      <button
        type="button"
        onClick={() => setOpen(!open)}
        style={{
          width: '100%',
          height: 38,
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          padding: '0 11px',
          border: '1px solid #dbe3ed',
          borderRadius: 7,
          background: '#fff',
          cursor: 'pointer',
          color: '#203150',
          fontSize: 14,
          borderColor: open ? '#83abfb' : '#dbe3ed',
          boxShadow: open ? '0 0 0 3px rgba(36, 104, 242, 0.08)' : 'none',
        }}
      >
        {selectedOption ? selectedOption.label : <span style={{ color: '#52627a' }}>{placeholder}</span>}
        <div style={{ marginLeft: 'auto', display: 'flex', gap: 4 }}>
          {value && (
            <X
              size={16}
              style={{ color: '#60708a', cursor: 'pointer' }}
              onClick={e => {
                e.stopPropagation();
                onChange(null);
              }}
            />
          )}
          <ChevronDown size={16} style={{ color: '#60708a', transform: open ? 'rotate(180deg)' : '', transition: 'transform 0.2s' }} />
        </div>
      </button>

      {open && (
        <div
          style={{
            position: 'absolute',
            top: '100%',
            left: 0,
            right: 0,
            background: '#fff',
            border: '1px solid #dbe3ed',
            borderRadius: 7,
            marginTop: 4,
            zIndex: 50,
            boxShadow: '0 4px 12px rgba(0, 0, 0, 0.1)',
          }}
        >
          <div style={{ padding: 8, borderBottom: '1px solid #edf1f5' }}>
            <div style={{ display: 'flex', gap: 8, alignItems: 'center', padding: '0 8px', height: 32, border: '1px solid #dbe3ed', borderRadius: 6, background: '#fafcff' }}>
              <Search size={14} style={{ color: '#60708a' }} />
              <input
                ref={inputRef}
                type="text"
                value={search}
                onChange={e => setSearch(e.target.value)}
                placeholder="Search..."
                style={{
                  flex: 1,
                  border: 'none',
                  outline: 'none',
                  background: 'transparent',
                  fontSize: 13,
                }}
              />
            </div>
          </div>
          <div style={{ maxHeight: 200, overflowY: 'auto' }}>
            {filtered.length === 0 ? (
              <div style={{ padding: 12, textAlign: 'center', color: '#60708a', fontSize: 13 }}>No results found</div>
            ) : (
              filtered.map(option => (
                <button
                  key={option.value}
                  type="button"
                  onClick={() => {
                    onChange(option.value);
                    setOpen(false);
                    setSearch('');
                  }}
                  style={{
                    width: '100%',
                    padding: '10px 12px',
                    border: 'none',
                    background: value === option.value ? '#edf4ff' : 'transparent',
                    color: value === option.value ? '#2468f2' : '#203150',
                    textAlign: 'left',
                    fontSize: 13,
                    cursor: 'pointer',
                    fontWeight: value === option.value ? 600 : 400,
                  }}
                  onMouseEnter={e => {
                    (e.currentTarget as HTMLButtonElement).style.background = '#f7f9fc';
                  }}
                  onMouseLeave={e => {
                    (e.currentTarget as HTMLButtonElement).style.background = value === option.value ? '#edf4ff' : 'transparent';
                  }}
                >
                  {option.label}
                </button>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
