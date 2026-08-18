// Browser-native printing: no server round trip, no PDF library.
//
// The printable document lives hidden in the DOM (.print-portal). On print we
// hide #root so only that portal reaches the paper, and the browser shows its
// own preview where the user can print or "Save as PDF".
//
// Pattern adapted from the BROMS project's frontend/src/lib/print.ts.

function sanitizeFilename(name: string): string {
  const cleaned = (name || '')
    .replace(/[\\/:*?"<>|]+/g, '-') // characters illegal in filenames
    .replace(/\s+/g, ' ')
    .trim()
    .slice(0, 120);
  return cleaned || 'UPVC-Document';
}

// Guard against React StrictMode's dev-only double mount-effect firing two
// print dialogs back to back. Cleared when afterprint fires.
let printing = false;

// Images (the business logo) load asynchronously. Printing before they decode
// gives a blank header on a cold cache, so wait — capped so a broken image
// can never hang printing.
function waitForPrintImages(): Promise<void> {
  const imgs = Array.from(document.querySelectorAll<HTMLImageElement>('.print-portal img'));
  if (!imgs.length) return Promise.resolve();
  const loaded = Promise.all(
    imgs.map(img => img.complete
      ? Promise.resolve()
      : new Promise<void>(resolve => {
          img.addEventListener('load', () => resolve(), { once: true });
          img.addEventListener('error', () => resolve(), { once: true });
        })),
  ).then(() => undefined);
  return Promise.race([loaded, new Promise<void>(r => setTimeout(r, 2000))]);
}

/**
 * Open the browser's print preview for the mounted .print-portal document.
 *
 * @param filename  suggested name in the Save-as-PDF dialog, e.g. "Quotation QT26-1"
 * @param opts.page paper size/orientation, injected as an UN-NAMED `@page` rule.
 *                  Named @page rules are silently ignored by older Chromium
 *                  (which is what a packaged desktop webview may be running),
 *                  so never rely on them.
 */
export function printDocument(
  filename: string,
  opts?: { page?: string; margin?: string; onDone?: () => void },
) {
  if (printing) return;
  printing = true;

  waitForPrintImages().then(() => {
    const prevTitle = document.title;
    document.title = sanitizeFilename(filename);
    document.body.classList.add('printing-a4');

    // Appended last so it wins over any earlier @page rule in the stylesheet.
    const pageStyle = document.createElement('style');
    pageStyle.setAttribute('data-print-page', '');
    pageStyle.textContent =
      `@media print { @page { size: ${opts?.page ?? 'A4 portrait'}; margin: ${opts?.margin ?? '12mm'}; } }`;
    document.head.appendChild(pageStyle);

    const cleanup = () => {
      document.body.classList.remove('printing-a4');
      pageStyle.remove();
      document.title = prevTitle;
      window.removeEventListener('afterprint', cleanup);
      printing = false;
      opts?.onDone?.();
    };
    window.addEventListener('afterprint', cleanup);
    window.print();
  });
}
