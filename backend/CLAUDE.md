# Backend CLAUDE.md

## Code Style

- Write clean, concise code - prioritize readability (code should be immediately understandable)
- Use type hints for all arguments and return values (strict Pyright configuration enforced)
- Prefer clear naming over explanatory comments
- Reference pyproject.toml for linter rules
- Import at the top of files, not within functions
- Use BaseReflectModel for all Pydantic schemas
- StrEnum should use auto() for enum values where possible
- Do NOT use tuples, use Pydantic models instead
- Reference code from surrounding files for convention
- Build all schemas in a schemas folder in the folder of the service that uses them
- Avoid `Any` type where possible
- NEVER use async code in pipeline services (AssetAnnotator, EditPlanner, EditExecutor)
- API routes use async for FastAPI compatibility
- NEVER ignore lint errors, either fix or ask the user how to proceed

## Service Class Development

- Never expose database models directly - wrap in schema types
- Provider function in `providers.py` (use `@cache` for singletons)

## Project Structure

```
src/
├── api/                    # FastAPI application
│   ├── main.py             # App entry point
│   ├── routes/             # REST endpoints
│   ├── websockets/         # WebSocket handlers
│   └── schemas/            # Request/response models
├── pipeline/               # Pipeline orchestration
│   ├── job_runner.py       # Runs full pipeline
│   └── progress_reporter.py # WebSocket broadcasting
├── common/                 # Shared models
├── mongodb/                # Database layer
├── asset_annotator/        # Service A: Analyze footage
├── style_extractor/        # Service B: Extract editing style
├── edit_planner/           # Service C: Plan the edit
└── edit_executor/          # Service D: Generate OTIO
```

## Running the Backend

```bash
cd backend
poetry install
poetry run uvicorn src.api.main:app --reload
```

## Environment Variables

Copy `.env.example` to `.env` and fill in:
- `OPENAI_API_KEY` - OpenAI API key for LLM agents
- `MONGODB_CONNECTION_STRING` - MongoDB connection string
- `MONGODB_DATABASE_NAME` - Database name (default: reflect_dev)
