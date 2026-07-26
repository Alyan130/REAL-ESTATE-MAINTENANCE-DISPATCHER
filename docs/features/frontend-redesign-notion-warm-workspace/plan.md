# Feature Plan: Front-End Redesign (Notion Warm Workspace)

## Context & Overview
The frontend UI is being updated to align with the "Notion Warm Workspace" design system specified in `docs/context/design.md`. The design features warm minimal surfaces, whisper borders, crisp typography (Inter and JetBrains Mono), pill-shaped interactive elements (buttons, badges), subtle multi-layer shadows, and Notion Blue (`#0075de` / `#005eb4`) as the primary accent color.

## Scope
- **Target Files**: All CSS styles, UI components, layout components, domain components, and pages inside `frontend/src/`.
- **Invariants**: No logic, state management, API routes, or backend interactions will be modified.

## Design Token Specs
- **Background & Canvas**: Warm paper off-white `#fff8f5` / `#ffffff`.
- **Surfaces**: Warm neutral palette (`#fbf2ee`, `#f5ece8`, `#efe6e2`, `#e9e1dd`, `#f6f5f4`).
- **Ink / Typography**: `#0f0c0a` (Quase Preto / High-Contrast Ink), `#1e1b19` (On-Surface Ink), `#454749` / `#414753` (Warm Muted Secondary).
- **Accent**: `#0075de` / `#005eb4` (Azul Notion Accent highlight, focus rings, primary action fills), `#e7eff5` (Soft Blue Tint).
- **Borders**: 1px ultra-fine whisper borders `rgba(0,0,0,0.08)` or `#e9e1dd`.
- **Shapes**:
  - Buttons, Badges, Pills: `rounded-full` (9999px).
  - Cards, Modals, Containers: `rounded-2xl` (1.5rem / 24px) or `rounded-xl` (1rem / 16px).
- **Shadows**: Soft multi-layer depth (`shadow-[0_2px_12px_rgba(0,0,0,0.04)]`, `shadow-[0_6px_20px_rgba(0,0,0,0.06)]`).

## Detailed Approach
1. **Globals & CSS**: Update `@theme` and base layer styles in `globals.css` with the warm workspace design tokens.
2. **Core UI System**:
   - `button.tsx`: Pill shapes (`rounded-full`), `#0075de` fill, hover lift, tactile press.
   - `card.tsx`: Warm background, `rounded-2xl`, whisper border `border-[#e9e1dd]`, soft shadow.
   - `badge.tsx`: Pill shapes (`rounded-full`), warm tinted status and category tones.
   - `field.tsx`: Warm input controls, `rounded-xl`, Notion Blue focus ring `#0075de`, clear labels.
   - `modal.tsx`: Warm overlay backdrop, `rounded-2xl` corners, whisper border headers.
   - `alert.tsx`, `empty-state.tsx`, `skeleton.tsx`, `confirm-dialog.tsx`, `page-header.tsx`, `toast-host.tsx`: Styled for warm minimalism.
3. **Layout & Shell**:
   - `app-shell.tsx`: Notion-inspired warm minimal sidebar (`#f6f5f4` / `#f5ece8`), pill nav items, active indicator line in `#0075de`, responsive mobile drawer.
   - `auth-layout.tsx`: Centered warm paper card layout.
4. **Domain & Page Components**:
   - `ticket-row.tsx`, `status-badge.tsx`, `ticket-filters.tsx`, `photo-grid.tsx`: Redesigned for warm minimalism and clear ticket status hierarchy.
   - Modal forms for Properties, Tenants, and Vendors.
5. **App Pages**:
   - Landing (`app/page.tsx`), Auth (`login/page.tsx`, `accept-invite/page.tsx`).
   - PM Dashboard & Detail pages (`(pm)/*`).
   - Tenant Ticket Submission & Tracking pages (`(tenant)/*`).
   - Vendor Portal Notice page (`vendor/page.tsx`).
