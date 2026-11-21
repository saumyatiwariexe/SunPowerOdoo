# Frontend agent instructions

- Put pages and feature-specific components in `src/features/<module>/`. Shared components, routing, and layout live in `src/app/`, owned by Person D.
- Use `src/app/api.js` for API requests so cookie credentials and response handling stay consistent.
- Start at phone width. Give warehouse scanning and crew workflows large inputs and touch targets.
- Show validation beside the relevant fields and preserve input after failed submissions.
- Give lists and details clear loading, empty, and error states. Use the shared Tailwind tokens and components.
