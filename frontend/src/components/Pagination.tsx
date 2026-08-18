import { useEffect, useMemo, useState } from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';

export const PAGE_SIZES = [20, 50, 100, 200];
export const DEFAULT_PAGE_SIZE = 20;

/**
 * Client-side paging for a list page.
 *
 * Returns the slice to render plus everything the <Pagination/> footer needs.
 * Pass the already-filtered rows: the page resets to 1 whenever the row count
 * changes, so searching or filtering never strands you on an empty page.
 */
export function usePagination<T>(rows: T[], initialSize = DEFAULT_PAGE_SIZE) {
  const [page, setPage] = useState(1);
  const [size, setSize] = useState(initialSize);

  const total = rows.length;
  const pageCount = Math.max(1, Math.ceil(total / size));

  useEffect(() => { setPage(1); }, [total, size]);

  const current = Math.min(page, pageCount);
  const pageRows = useMemo(
    () => rows.slice((current - 1) * size, current * size),
    [rows, current, size],
  );

  return {
    pageRows,
    props: {
      page: current, pageCount, total, size,
      from: total === 0 ? 0 : (current - 1) * size + 1,
      to: Math.min(current * size, total),
      onPage: setPage, onSize: setSize,
    },
  };
}

export interface PaginationProps {
  page: number; pageCount: number; total: number; size: number;
  from: number; to: number;
  onPage: (p: number) => void;
  onSize: (s: number) => void;
  noun?: string;
}

export default function Pagination({
  page, pageCount, total, size, from, to, onPage, onSize, noun = 'entries',
}: PaginationProps) {
  // A short window of page numbers around the current one, so 500 pages don't
  // produce 500 buttons.
  const windowed = useMemo(() => {
    const span = 2;
    const out: (number | '...')[] = [];
    let last = 0;
    for (let p = 1; p <= pageCount; p++) {
      const near = Math.abs(p - page) <= span;
      if (p === 1 || p === pageCount || near) {
        if (last && p - last > 1) out.push('...');
        out.push(p);
        last = p;
      }
    }
    return out;
  }, [page, pageCount]);

  return (
    <div className="pagination">
      <span>{total === 0 ? `No ${noun}` : `Showing ${from}-${to} of ${total} ${noun}`}</span>
      <div className="pagination-controls">
        <button className="page-chip" disabled={page <= 1} onClick={() => onPage(page - 1)} title="Previous page">
          <ChevronLeft size={14} />
        </button>
        {windowed.map((p, i) => p === '...'
          ? <span key={`gap${i}`} className="page-gap">...</span>
          : <button key={p} className={`page-chip${p === page ? ' active' : ''}`} onClick={() => onPage(p)}>{p}</button>)}
        <button className="page-chip" disabled={page >= pageCount} onClick={() => onPage(page + 1)} title="Next page">
          <ChevronRight size={14} />
        </button>
        <select className="input select page-size" value={size} onChange={e => onSize(Number(e.target.value))}>
          {PAGE_SIZES.map(s => <option key={s} value={s}>{s} / page</option>)}
        </select>
      </div>
    </div>
  );
}
