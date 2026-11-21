---
name: react-feature-page
description: Use when building React list, form, detail, or print views for a feature.
---

# Build a React feature page

1. Use `docs/FEATURES_BY_ROLE.md` to identify the role, screens, and endpoints. Put the feature under `frontend/src/features/<module>/` and coordinate routes with Person D.
2. Use `src/app/api.js` for requests. Render the `data` payload, use pagination metadata on lists, and use the API error envelope for failures.
3. Lists show loading, empty, and retryable error states. Details handle missing records and show actions that match the user's role and the record's current state.
4. Forms validate inline, map server field errors to inputs, preserve values on failure, and disable duplicate submission while saving. Show rule failures returned by the API near the action.
5. Start with a narrow, single-column layout and large touch targets. Add wider layouts at the existing Tailwind breakpoints. Use shared Tailwind tokens and components from `src/app/`.
6. Give quotes and invoices a printable view using the same API record. Use print styles to hide navigation and actions, keep totals visible, and avoid splitting line items. Check print preview.
