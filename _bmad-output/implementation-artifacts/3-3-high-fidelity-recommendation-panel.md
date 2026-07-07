---
baseline_commit: 0c73971bbed139e82ed7b68124b6ec545a88f65a
---

# Story 3.3: High-Fidelity Recommendation Panel

Status: done

## Story

As a kiosk customer,
I want to see recommended items presented in an elegant, animated layout with personalized promotional copy and clear reasons,
so that I can easily decide to add recommended items to my cart.

## Acceptance Criteria

1. **Bento Grid Layout**: Recommendations must be displayed in an asymmetric, gapless Bento Grid of interlocking cells using `grid-flow-dense` and column/row spans, mixing text, pricing, and visual imagery (UX-DR3).
2. **Double-Bezel Card Design**: Each card container must utilize the "double-bezel" (Doppelrand) card design: a nested layout with an outer shell (`border border-black/5` or `border-white/10`) and a concentrically smaller inner core with an inset highlight shadow (UX-DR2).
3. **Rounded Pill Action Buttons**: All recommendation action buttons must be fully rounded pills with a button-in-button trailing icon format (e.g., plus icon inside a smaller nested circle) (UX-DR4).
4. **Staggered Animations & Hover/Active States**: Cards must slide up and fade in with staggered entry animations (UX-DR7). They must have haptic hover states (scale up `scale-102` or `1.02` with diagonal icon translate) and active states (pressed scaling `scale-[0.98]`) with a custom cubic-bezier transition (UX-DR5).
5. **GenAI Copy & Rationale Display**: Each recommendation must display clear Vietnamese promotional copy and its statistical co-occurrence rationale in a secondary stats text field (UX-DR8).

## Tasks / Subtasks

- [x] **Task 1: Update CSS for Bento Grid layout and interlocking spans** (AC: 1)
- [x] **Task 2: Implement "double-bezel" styling and haptic interactions for tiles** (AC: 2, 4)
- [x] **Task 3: Style the button-in-button trailing icon primary buttons** (AC: 3)
- [x] **Task 4: Update recommendation rendering in `app.js` with animations and correct HTML structure** (AC: 1, 2, 3, 4, 5)
- [x] **Task 5: Verify recommendations look correct in Kiosk UI** (AC: 1-5)

## Dev Agent Record

### Agent Model Used

Gemini 3.5 Flash (High)

## Dev Notes

- Make sure to use the existing styles or extend them.
- In `static/app.js`, update `renderRecommendations` to apply classes like `.col-span-2` or `.row-span-2` based on index or item score to form an asymmetric bento grid.
- Keep animations smooth.
