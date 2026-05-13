# Implementation Plan for PM Dashboard CRUD APIs

This implements the feature to properly organize the REST endpoints into resources while introducing new read/update operations for Properties, Tenants, and Vendors. 

## Scope & Objective
- Consolidate all authentication and invitation-related operations into `auth.py`.
- Create dedicated routers for Properties, Tenants, and Vendors.
- Implement CRUD operations as requested.
- Ensure strict JWT token verification and role-based access control (PM only for these endpoints).

## Proposed Changes

### Routes Refactoring & Creation

#### [MODIFY] auth.py
Move tenant/vendor creation endpoints from `pm.py` to `auth.py`.
- Endpoints:
    - `POST /auth/invites/tenants` (Create tenant invite)
    - `POST /auth/invites/vendors` (Create vendor invite)
    - `POST /auth/invites/tenants/{tenant_id}/resend` (Resend tenant invite)
    - `POST /auth/invites/vendors/{vendor_id}/resend` (Resend vendor invite)
- Tag: `invites`

#### [NEW] properties.py
- `POST /properties`: Create new property. `pm_id` from JWT.
- `GET /properties`: List properties for logged-in PM.
- `GET /properties/{property_id}`: Get property details.
- `DELETE /properties/{property_id}`: Soft delete (set `is_active=False`).
- Tag: `properties`

#### [NEW] tenants.py
- `GET /tenants`: List tenants, optional `property_id` filter.
- `GET /tenants/{tenant_id}`: Get tenant details.
- `DELETE /tenants/{tenant_id}`: Deactivate tenant.
- Tag: `tenants`

#### [NEW] vendors.py
- `GET /vendors`: List vendors for logged-in PM.
- `GET /vendors/{vendor_id}`: Get vendor details.
- `DELETE /vendors/{vendor_id}`: Deactivate vendor.
- Tag: `vendors`

#### [DELETE] pm.py
Remove file once all logic is migrated.

#### [MODIFY] main.py
Include new routers and remove `pm` router.

## Resource Modeling & Constraints
- **Security**: Every endpoint must use `PMUserDep` (or similar) to ensure the user is authenticated and has the 'PM' role.
- **Ownership**: When fetching or modifying a resource by ID (Property, Tenant, Vendor), verify it belongs to the authenticated PM.
- **Soft Delete**: Records should not be hard-deleted but marked as `is_active=False`.

## Exclusions
- Automated tests (per user request).
- Concurrent server execution (per user request).
