# Foundation: Utilities, Login & Middleware

Implementing the core cryptographic and token infrastructure, login endpoint, and auth middleware. These are critical for the application's overall testability and authentication structure.

## Proposed Changes

### Configuration and Infrastructure
#### [MODIFY] [backend/requirements.txt](file:///d:/next_js/projects/REAL-ESTATE-MAINTENANCE-DISPATCHER/backend/requirements.txt)
- Add `fastapi[standard]`
- Add `pydantic-settings`
- Add `bcrypt` (for password hashing)
- Add `PyJWT` (for token management)

#### [NEW] [backend/core/config.py](file:///d:/next_js/projects/REAL-ESTATE-MAINTENANCE-DISPATCHER/backend/core/config.py)
- Create `Settings` model.
- Include `JWT_SECRET_KEY` and `BCRYPT_WORK_FACTOR` (default: 12) settings.

#### [NEW] [backend/main.py](file:///d:/next_js/projects/REAL-ESTATE-MAINTENANCE-DISPATCHER/backend/main.py)
- Main FastAPI entry point integrating routers.

---

### Core Security Utilities
#### [NEW] [backend/core/security.py](file:///d:/next_js/projects/REAL-ESTATE-MAINTENANCE-DISPATCHER/backend/core/security.py)
- `hash_password(plain: str) -> str`: Uses `bcrypt` initialized with `BCRYPT_WORK_FACTOR`.
- `verify_password(plain: str, hashed: str) -> bool`: Safe verification using `bcrypt`.
- `create_token(user_id, role, token_type) -> str`: JWT Token creation supporting `login` (60 days), `invite` (48 hours), `reset` (1 hour) logic with strict `payload` mapping.
- `decode_token(token: str) -> dict`: Validates expirations and signature ensuring non-expired valid JSON.

---

### API Endpoints & Middleware
#### [NEW] [backend/api/deps.py](file:///d:/next_js/projects/REAL-ESTATE-MAINTENANCE-DISPATCHER/backend/api/deps.py)
- `get_current_user` generic dependency: Retrieves `Authorization` bearer token, uses `decode_token` mapping `sub` property to existing active user in the database. Returns an SQLAlchemy `User` instance, or throws standardized HTTP `401` on failure.

#### [NEW] [backend/api/routes/auth.py](file:///d:/next_js/projects/REAL-ESTATE-MAINTENANCE-DISPATCHER/backend/api/routes/auth.py)
- `POST /auth/login` schema consuming `LoginRequest` (`email`, `password`).
- Verifies hashed passwords mapped against user by `email`.
- Checks for `is_active` parameter explicitly asserting `invite_status == 'approved'`, or raises `401` and `403` correspondingly.

---

## Verification Plan

### Automated Tests
1. **Initialize Testing Environment**: Configure a test db fixture in pytest. We will add `pytest`, `pytest-asyncio`, and `httpx`.
2. **Execute Utilities Tests**: Construct mock calls proving `hash_password` and `verify_password` work strictly to spec, alongside `create_token` & `decode_token` expiration/payload parameters matching criteria identically.
3. **Execute API Tests**: Start `TestClient` mimicking `POST /auth/login` checks:
    - Pass valid creds -> Ensure JWT exists
    - Invalid pass -> Validate exact 401 returns
    - Check invite pending status returns exactly 403
4. **Middleware Tests**: Mimic access to a dummy protected route demonstrating missing/failing auth correctly kicks out unauthenticated traffic (401).

Run via standard testing setup: `pytest backend/tests/test_auth.py -v`.
