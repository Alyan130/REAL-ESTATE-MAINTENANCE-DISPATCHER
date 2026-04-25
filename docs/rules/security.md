# Security Rules

- Never commit secrets, API keys, or credentials — use environment variables only.
- All environment variables must be documented in `.env.example` with placeholder values.
- All API routes must validate the authenticated user before accessing any data.
- Tenant data is scoped to their property — never expose cross-property data in any query.
- Vendor portal access is token-gated — no unauthenticated endpoints.
- All file uploads (photos, invoices) go through Supabase Storage — never stored locally or served directly.
- Never log sensitive data (passwords, tokens, personal info) in any environment.