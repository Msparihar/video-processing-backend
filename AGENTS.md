# Agent Guidelines for Video Processing Backend

## Build/Lint/Test Commands

### Development Setup
- Install dependencies: `uv sync`
- Start services: `docker-compose up -d`
- Run app: `uv run uvicorn app.main:app --host 0.0.0.0 --port 8000`
- Run worker: `uv run celery -A app.celery_app worker --loglevel=info --concurrency=1 -Q default`

### Testing
- Integration tests: `uv run python test_overlay.py` (tests video upload/processing/download)
- Connection tests: `uv run python test_connections.py` (tests DB/Redis connectivity)
- No unit test framework configured - use manual integration tests

### Type Checking
- Run mypy: `uv run mypy app/` (if mypy is installed)
- Note: Current codebase has SQLAlchemy Column type issues that need fixing
- Access column values using `.file_path` instead of passing Column objects directly

### Database
- Create tables: `uv run python create_tables.py`
- Run migrations: `uv run alembic upgrade head`

## Code Style Guidelines

### Imports
- Standard library imports first
- Third-party imports second (fastapi, sqlalchemy, etc.)
- Local imports last with absolute paths
- Group imports by category with blank lines

### Naming Conventions
- Functions/variables: `snake_case`
- Classes: `PascalCase`
- Constants: `UPPER_CASE`
- Database columns: `snake_case`
- API endpoints: `snake_case`

### Type Hints
- Use type hints for all function parameters and return values
- Use `Optional[T]` for nullable types
- Use `List[T]`, `Dict[K,V]` for collections
- Use `Union[T1, T2]` for multiple possible types

### Error Handling
- Use `HTTPException` for API errors with appropriate status codes
- Use try/except blocks for file operations and external service calls
- Log errors with `logger.warning()` or `logger.error()`
- Clean up resources (files) in exception handlers
- Initialize variables before try blocks to avoid "possibly unbound" errors

### Database Patterns
- Use SQLAlchemy ORM with declarative models
- Use `relationship()` for foreign keys
- Use timezone-aware `DateTime(timezone=True)` for timestamps
- Use `server_default=func.now()` for auto-timestamps
- Use `uuid.uuid4()` for primary keys
- **IMPORTANT**: Access column values as attributes (e.g., `video.file_path`) not as Column objects

### Service Layer
- Use static methods in service classes
- Separate business logic from API endpoints
- Return boolean success indicators from processing methods
- Use transactions for multi-step operations

### File Operations
- Use `os.path.join()` for path construction
- Use `os.makedirs(exist_ok=True)` for directory creation
- Use context managers for file operations
- Validate file types and sizes before processing

### Async Patterns
- Use synchronous processing for simple operations
- Use Celery for long-running video processing tasks
- Poll task status for async operations
- Store task results in database

### Configuration
- Use Pydantic `BaseSettings` for configuration
- Load from environment variables with `.env` file
- Use sensible defaults for development

### Logging
- Use `logging.getLogger(__name__)` for module loggers
- Log at appropriate levels (debug, info, warning, error)
- Include relevant context in log messages

### API Design
- Use FastAPI with automatic OpenAPI generation
- Use Pydantic models for request/response validation
- Use dependency injection for database sessions
- Return structured JSON responses
- Use appropriate HTTP status codes

### Security
- Validate file uploads by type and size
- Use secure file paths and names
- Sanitize user inputs
- Use HTTPS in production