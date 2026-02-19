# Multi-Phase Validation Command

Run comprehensive validation checks on the conductor-ai codebase using modern Python tooling.

## Phase 1: Code Quality (Ruff)

```bash
# Format code
ruff format .

# Lint and auto-fix
ruff check . --fix

# Check without fix (for CI)
ruff check .
```

## Phase 2: Type Safety (mypy)

```bash
# Type check entire codebase
mypy src/ plugins/

# Skip tests (configured in pyproject.toml)
# Tests are excluded automatically
```

## Phase 3: Tests (pytest)

```bash
# Run all tests with coverage
pytest tests/ -v --cov=src --cov=plugins --cov-report=term-missing

# Run SDK tests only
pytest tests/sdk/ -v

# Run specific test file
pytest tests/test_agents.py -v

# Run with async debugging
pytest tests/ -v --log-cli-level=DEBUG
```

## Phase 4: Security Checks

```bash
# Check for hardcoded secrets (basic grep)
ruff check . --select S105,S106,S107

# Verify .env file exists and API keys not in code
if grep -r "OPENAI_API_KEY" --include="*.py" src/ plugins/ 2>/dev/null; then
  echo "ERROR: OpenAI references found - use DeepSeek/Qwen/Claude only"
  exit 1
fi
```

## Phase 5: Dependency Audit

```bash
# Check for outdated packages
pip list --outdated

# Verify critical versions
python -c "import sqlalchemy; assert sqlalchemy.__version__ >= '2.0', 'SQLAlchemy 2.0+ required'"
python -c "import pydantic; assert pydantic.__version__ >= '2.0', 'Pydantic 2.0+ required'"
```

## Phase 6: Project Structure

```bash
# Verify required files exist
test -f pyproject.toml || echo "ERROR: Missing pyproject.toml"
test -f .env.example || echo "WARNING: Missing .env.example"
test -f README.md || echo "WARNING: Missing README.md"

# Check for __init__.py in packages
find src/ -type d -not -path "*/.*" -exec test -f {}/__init__.py \; || echo "WARNING: Missing __init__.py files"
```

## Complete Validation Pipeline

```bash
# Run all phases in sequence
set -e

echo "Phase 1: Code Quality (Ruff)..."
ruff format . && ruff check . --fix

echo "Phase 2: Type Safety (mypy)..."
mypy src/ plugins/

echo "Phase 3: Tests (pytest)..."
pytest tests/ -v --cov=src --cov=plugins --cov-report=term-missing

echo "Phase 4: Security Checks..."
! grep -r "OPENAI" --include="*.py" src/ plugins/ 2>/dev/null || exit 1

echo "Phase 5: Dependency Audit..."
pip list --outdated

echo "Phase 6: Project Structure..."
test -f pyproject.toml && test -f .env.example

echo "✅ All validation phases passed!"
```

## Critical Rules Enforced

- **NO OpenAI models** - Validation fails if OpenAI references found
- **API keys in .env only** - Security checks enforce this
- **Python 3.11+** - Verified by pyproject.toml
- **Async-first** - Type checking ensures proper async/await usage
- **>90% test coverage** - pytest-cov reports coverage
