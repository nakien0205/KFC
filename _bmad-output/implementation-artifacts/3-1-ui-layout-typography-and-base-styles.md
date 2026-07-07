---
baseline_commit: NO_VCS
---

# Story 3.1: UI Layout, Typography, and Base Styles

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a kiosk customer,
I want to see a visually stunning, high-fidelity ordering screen with premium styling, typography, and a cohesive layout,
so that my first impression of the ordering experience feels premium, clean, and modern.

## Acceptance Criteria

1. **Static Directory Structure**: All frontend UI files must reside inside a dedicated `static/` directory (AD-6).
2. **KFC Brand Color Palette**: Use a premium red and white palette staying true to KFC's original brand colors:
   - Clean white or warm-white backgrounds (e.g., `#F9F9F6` or similar premium warm-white HSL).
   - Rich red brand accents (e.g., KFC signature red `#E4002B` or similar rich HSL).
   - Sharp near-black typography (e.g., `#111111` or `#1E1E1E` for high readability; avoid pure black `#000000`).
   - Soft grey highlights and borders (e.g., `border-black/5` or `border-black/10` to keep separations clean).
   - Subtle noise texture or grain overlay on the background for a premium paper feel (UX-DR6).
   - Strictly avoid generic AI purple/neon glows.
3. **Premium Typography System**:
   - Load and use a premium sans-serif typography system (e.g., Outfit or Inter via Google Fonts) for display/body text (UX-DR1).
   - Use Geist Mono (or Outfit Mono/standard monospace) for code, numbers, prices, and labels (UX-DR1).
   - All display headlines (H1/H2) must be restricted to a maximum of 2 lines on desktop with strict line-height/descender clearance (UX-DR1).
4. **Responsive Layout Skeleton**:
   - Build a modern single-page layout structure.
   - On desktop, it must display a multi-column kiosk interface (e.g., main ordering menu/categories on the left/center, cart/checkout panel on the right).
   - On mobile screens (below `768px`), the layout must adapt responsively to a single-column stack.
5. **Interactive Base Element Styles**:
   - **Double-Bezel (Doppelrand) Container**: All card containers (menu cards, checkout panels) must utilize a nested double-bezel layout: an outer shell with a subtle background border (`border border-black/5` or similar) and padding, containing an inner core with a smaller, concentrically calculated border-radius and inset highlight shadow (`shadow-[inset_0_1px_rgba(255,255,255,0.15)]` or similar light/dark inset depending on backdrop color) (UX-DR2).
   - **Rounded Pill Action Buttons**: All primary action buttons (e.g., "Add to Cart", "Select Promotion") must be fully rounded pills (UX-DR4).
   - **Haptic Animation Utilities**: Establish transitions using a custom cubic-bezier curve (`transition: all 700ms cubic-bezier(0.32, 0.72, 0, 1)`) (UX-DR5). Set up scale-up hover state (`scale(1.02)`) and scale-down active state (`scale(0.98)`) (UX-DR5).

## Tasks / Subtasks

- [x] **Task 1: Setup static assets directory & HTML skeleton** (AC: 1, 2, 3)
  - [x] Create `static/` directory in the project root.
  - [x] Create `static/index.html` structure with semantic HTML5 elements.
  - [x] Load Outfit and Geist Mono fonts via Google Fonts `<link>` tags in `index.html`.
- [x] **Task 2: Implement styling core and design system variables** (AC: 2, 3)
  - [x] Create `static/style.css`.
  - [x] Define CSS Custom Properties (variables) for the KFC red-white palette, font scales, line-heights, shadows, and transition curves.
  - [x] Implement a subtle noise texture/grain overlay utility (e.g., CSS background SVG noise or data URI).
- [x] **Task 3: Implement responsive layout skeleton** (AC: 4)
  - [x] Set up main flexbox/grid layout for desktop: categories sidebar, middle menu list, and right checkout panel.
  - [x] Write media queries to collapse layout to a single column stack below `768px`.
- [x] **Task 4: Implement base UI components (Button, Bezel container, Typography utility classes)** (AC: 5)
  - [x] Define CSS classes for the double-bezel (Doppelrand) container with inset highlight.
  - [x] Define CSS classes for fully rounded pill buttons with custom cubic-bezier transitions.
  - [x] Define hover/active state CSS rules using the custom scale transforms.
- [x] **Task 5: Serve Static Directory on FastAPI Server** (AC: 1)
  - [x] Update `main.py` to mount the `static/` directory using FastAPI's `StaticFiles` at `/static` and serve `index.html` on the root route `/`.
  - [x] Verify local server serves the index.html page and static assets successfully.

### Review Findings

- [x] [Review][Patch] H2 headlines lack line restriction [static/style.css:623]
- [x] [Review][Patch] Inner bezel border-radius not concentric [static/style.css:519]
- [x] [Review][Patch] Primary buttons lack correct haptic hover and active scale [static/style.css:568]
- [x] [Review][Patch] Missing static directory auto-creation check on startup [main.py:102]
- [x] [Review][Patch] Mixed English/Vietnamese language in sidebar categories [static/index.html:203]
- [x] [Review][Defer] Frontend HTML contains no interactive JS file [static/index.html:185] — deferred, pre-existing
- [x] [Review][Defer] Unit test check live API if GEMINI_API_KEY set [test_main.py:862] — deferred, pre-existing
- [x] [Review][Defer] Weak assertions in TestMainAPI [test_main.py:845] — deferred, pre-existing
- [x] [Review][Defer] Lifespan ignores critical data load failures [main.py:35] — deferred, pre-existing
- [x] [Review][Defer] Sync requests block FastAPI thread [main.py:123] — deferred, pre-existing
- [x] [Review][Defer] Optional request fields hide bugs [main.py:108] — deferred, pre-existing
- [x] [Review][Defer] Dangerous price fallback to 0.0 [main.py:137] — deferred, pre-existing
- [x] [Review][Defer] Global cache read/write thread safety issues [main.py:20] — deferred, pre-existing
- [x] [Review][Defer] Flawed chicken matching substring checks [recommender.py:7] — deferred, pre-existing

## Dev Notes

- **Directory Structure (AD-6)**: Frontend files must live in `static/` under the project root.
- **Serving static files in FastAPI**: Keep `main.py` stateless and clean. Add `from fastapi.staticfiles import StaticFiles` to serve the UI.
- **Vietnamese Dong Representation**: Kiosk prices must be formatted in VND (e.g., `20.000đ`). Keep typography rules aligned (using Geist Mono for numbers/prices).

### Project Structure Notes

- New folder: `static/`
- New files: `static/index.html`, `static/style.css`
- Modified files: `main.py` (to mount static files)

### References

- [SPEC.md](file:///d:/Python/Projects/KFC/_bmad-output/specs/spec-kfc-kiosk-recommender/SPEC.md#L31-L33) (CAP-5)
- [ARCHITECTURE-SPINE.md](file:///d:/Python/Projects/KFC/_bmad-output/planning-artifacts/architecture/architecture-kfc-rag-system-2026-07-06/ARCHITECTURE-SPINE.md#L69-L73) (AD-6)
- [epics.md](file:///d:/Python/Projects/KFC/_bmad-output/planning-artifacts/epics.md#L52-L60) (UX-DR1 to UX-DR6)

## Dev Agent Record

### Agent Model Used

Gemini 3.5 Flash (High)

### Debug Log References

- FastAPI TestClient requests to `/` and `/static/style.css` returned 200 OK with correct Content-Type.
- Verified Outfit font loading and fallback sans-serif configuration.
- Verified Geist Mono styling for pricing labels and badges.

### Completion Notes List

- Created `static/index.html` structure with semantic elements, including brand stripe and responsive grid columns.
- Created `static/style.css` containing premium color tokens, custom transition variables, double-bezel inner/outer borders, fully rounded pill button styles, and SVG fractalNoise background overlay.
- Mounted FastAPI `StaticFiles` and registered `/` home route returning index.html as a `FileResponse`.
- Added unit tests in `test_main.py` to assert correct response codes and headers for index and CSS routes.

### File List

- `static/index.html`
- `static/style.css`
- `main.py`
- `test_main.py`
