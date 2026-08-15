---
name: ui-legibility
description: Keeps UPVC Pro's UI legible, uncluttered, and stable instead of cramming data at illegible font sizes. Use before and after any change to frontend/src/styles.css, or any page/component that adds a table column, metric, badge, or form field. Also use when the user says the UI feels "too dense," "too small," "cluttered," or asks for a UI/UX pass.
---

# UI Legibility for UPVC Pro

This app is a data-heavy ERP (tables, forms, dashboards), and the natural failure mode is solving "too much data" by shrinking fonts and packing more columns in, rather than by prioritizing what's shown. Both parts matter equally: type scale and information density.

## Why this exists

An audit of `frontend/src/styles.css` (2026-07) found ~70 `font-size` declarations, many between 8.5px and 10.5px — table headers at 9.5px, footer/badges/captions at 10px, some labels as low as 8.5px. That is below a comfortable reading floor for a desktop business app. The fix applied then: a uniform type-scale raise (see the mapping in git history / PROJECT_STATUS.md) with a floor around 11.5px for the smallest captions and 12.5-13px for table cells. Treat that as the current baseline — don't reintroduce sizes below it.

## Type scale rules

- **Floor: 11.5px.** Nothing in the UI should render smaller than that — not captions, not badges, not table sub-text. If something feels like it needs to be smaller to fit, the real problem is too much content in that space, not the font.
- **Table cells: 12.5-13px. Table headers: 12-12.5px, weight 600-700 to stay legible at a slightly smaller size than body text.**
- **Body text: 14px baseline.** Page titles/headers scale up from there (15/16/18/20/24/28px steps already exist in the codebase — reuse them, don't invent new ones).
- When adding a new component, match font-size to the closest existing class in `styles.css` rather than picking a new raw px value. Search for a sibling class first (e.g. a new summary panel should reuse `.summary-line` / `.metric-copy` sizing, not invent its own).
- Check any fixed-height container (`height:`, not `min-height:`) after changing its font-size — badges, pills, icon circles, and `.editable-table input/select` are the ones in this codebase most likely to clip text if the font grows and the box doesn't.

## Data density rules

Small fonts are usually a symptom of trying to show too many columns/fields at once, not a cause on its own. Before shrinking anything, ask whether everything currently shown needs to be there:

- **Tables**: aim for 6-9 visible columns before reaching for horizontal scroll or restructuring. If a table needs more than that (e.g. Create Quotation's item grid currently has 13 columns: S.No, Price Master, Category, Style, HSN, Width, Height, SFT, Qty, Total SFT, Rate, Amount, Location, Action), prefer:
  - Moving rarely-glanced-at columns (spec fields like Profile/Color/Track, or a raw HSN code) into an expandable row, a details drawer, or a secondary panel instead of the main scan line.
  - Grouping related numeric columns (e.g. Width + Height into one "Size" cell like the PDF already does: `f"{width} x {height} mm"`) rather than giving each its own column.
- **Dashboards/cards**: a metric card should show one number and one caption, not multiple stacked facts. If a card needs a legend, it's probably two cards.
- **Forms**: group related fields visually (existing `.form-grid` / `Field` pattern) rather than adding more fields to a flat list.
- Don't solve "this table is too wide for the viewport" by shrinking the font further — that's the anti-pattern this skill exists to stop. Solve it by removing/relocating columns, or accept horizontal scroll for a genuinely rare power-user table.

## Process when doing a UI pass

1. Read the current `font-size` and `height`/`min-height` values for the component you're touching before changing them — don't guess.
2. After a CSS change, verify live in the browser (per this project's standing rule: check real DB-backed pages, not just one component in isolation) — take a screenshot of at least one list page, one dashboard-style page, and one dense form/table page, since a shared class change ripples across the whole app.
3. Check both a normal viewport and the app's current `min-width: 1180px` floor (in `:root`/`html,body,#root`) — this app does not support narrower viewports today, so don't test against mobile widths unless that's a separate, explicit ask.
4. If a genuinely wide table (13+ columns) needs restructuring, treat that as its own scoped task — confirm with the user which columns are "at a glance" essential vs. supplementary before removing/relocating anything, since that's a product decision, not just a style one.
