# Implementation Plan: Tickets CRUD APIs

This feature implements complete Ticket management for Tenants and Property Managers, utilizing Supabase Storage for media attachments and FastAPI BackgroundTasks for responsive, non-blocking submission.

## Scope
- **Create Ticket**: Non-blocking flow for Tenants to submit maintenance requests with photos.
- **List Tickets**: Role-based access (PMs see all property tickets; Tenants see only theirs).
- **Get Ticket**: Detailed view for a single ticket.
- **Update Status**: Restricted to PMs for advancing the maintenance workflow.

## Technical Decisions
- **Background Processing**: To ensure a near-instant response to the client, the actual upload of images to Supabase Storage and final database enrichment will occur in a FastAPI `BackgroundTasks` function.
- **Storage**: Supabase Storage (`supabase` Python SDK) will be used to host ticket photos.
- **Database Architecture**: Tickets are linked to a `Tenant` and a `Property`.
- **RBAC**: strictly enforced via `CurrentUserDep` and `PMUserDep`.

## Implementation Approach

### 1. Storage Utility
- Create `backend/core/storage.py` to initialize the Supabase client and provide helper functions for async file uploads.

### 2. Non-blocking Ticket Submission (`POST /tickets`)
1. **Request**: Handled as `Multipart/Form-Data` to receive fields and binary files.
2. **Identity**: Extract `user_id` from JWT. Fetch `tenant_id` and `property_id`.
3. **Skeleton Creation**: Generate a `ticket_id` (UUID) and save a skeleton record to the DB with status `PENDING_UPLOAD`.
4. **Immediate Response**: Return the `ticket_id` to the frontend.
5. **Background Task**:
   - Stream each file to `tickets/{ticket_id}/{filename}` in Supabase.
   - Collect public/signed URLs.
   - Update the Ticket record with `media_urls`.
   - Set status to `OPEN`.
   - Trigger placeholder intake agent function.

### 3. Retrieval and Management
- **List (`GET /tickets`)**: 
  - PM: Optional filters for `property_id`, `status`, `category`. Filters by owned properties.
  - Tenant: Hard-coded filter to only show tickets where `tenant_id` matches their profile.
- **Get (`GET /tickets/{ticket_id}`)**: Validates ownership before returning details.
- **Update Status (`PATCH /tickets/{ticket_id}/status`)**: 
  - Restricted to PM role.
  - Updates the ticket state machine (e.g., OPEN -> TRIAGED).

## Required .env
- `SUPABASE_URL`
- `SUPABASE_KEY`
- `SUPABASE_STORAGE_BUCKET=tickets`

## Constraints
- No automated tests during this phase.
- No server execution during implementation.
- All code must include proper typing and generic error handling.
