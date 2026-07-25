```
myapp/
├── app/
│   ├── __init__.py
│   ├── main.py                 # Application factory
│   ├── config.py               # Settings management
│   ├── database.py             # Database session setup
│   ├── dependencies.py         # Shared dependencies
│   ├── exceptions.py           # Custom exception handlers
│   ├── middleware.py            # Custom middleware
│   ├── api/
│   │   ├── __init__.py
│   │   ├── router.py           # Root router aggregation
│   │   ├── v1/
│   │   │   ├── __init__.py
│   │   │   ├── router.py       # v1 router
│   │   │   ├── users.py        # User endpoints
│   │   │   ├── orders.py       # Order endpoints
│   │   │   └── auth.py         # Auth endpoints
│   │   └── v2/
│   │       └── ...
│   ├── models/
│   │   ├── __init__.py
│   │   ├── base.py             # SQLAlchemy base
│   │   ├── user.py
│   │   └── order.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── user.py             # Pydantic schemas
│   │   └── order.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── user_service.py     # Business logic
│   │   └── order_service.py
│   ├── repositories/
│   │   ├── __init__.py
│   │   ├── base.py             # Generic repository
│   │   ├── user_repo.py
│   │   └── order_repo.py
│   └── core/
│       ├── __init__.py
│       ├── security.py         # JWT, hashing
│       └── logging.py          # Structured logging
├── migrations/
│   └── versions/
├── tests/
│   ├── conftest.py
│   ├── test_users.py
│   └── test_orders.py
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
├── alembic.ini
└── .env.example
```