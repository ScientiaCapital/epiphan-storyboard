# Execute PRP (Planning & Review Protocol)

Execute a PRP implementation plan with 6-phase validation at each checkpoint.

## Usage

```
/execute-prp PRPs/[feature-name]-[YYYYMMDD].md
```

## Execution Workflow

### Phase 1: Preparation (Pre-flight)

**Verify prerequisites before starting:**

```bash
# 1. Ensure clean git state
git status | grep "working tree clean" || echo "ERROR: Uncommitted changes"

# 2. Create feature branch
git checkout -b feature/[feature-name]

# 3. Verify environment
source venv/bin/activate  # or conda activate conductor-ai
python --version | grep "3.1[12]"  # Python 3.11+

# 4. Install dev dependencies
pip install -e ".[dev]"

# 5. Run baseline validation
pytest tests/ -v  # Should all pass before starting
```

**Checklist:**
- [ ] Git working tree clean
- [ ] Feature branch created
- [ ] Python 3.11+ active
- [ ] Dependencies installed
- [ ] Baseline tests passing

---

### Phase 2: Foundation Implementation

**Execute Phase 1 tasks from PRP:**

```bash
# Example: Building SDK components
# 1. Create base classes
touch src/sdk/[new_feature].py

# 2. Add type hints
# Use Pydantic v2 models, TypedDict, or dataclasses

# 3. Write unit tests FIRST (TDD)
touch tests/test_[new_feature].py

# Run tests (should fail initially - RED)
pytest tests/test_[new_feature].py -v

# Implement minimum code to pass (GREEN)
# Refactor (REFACTOR)
```

**Validation Checkpoint:**
```bash
# Run ruff
ruff format src/ tests/
ruff check src/ tests/ --fix

# Run mypy
mypy src/sdk/[new_feature].py

# Run tests for this component
pytest tests/test_[new_feature].py -v --cov=src/sdk/[new_feature]
```

**Checklist:**
- [ ] Base classes created with type hints
- [ ] Unit tests written (TDD: RED → GREEN → REFACTOR)
- [ ] ruff format + check passes
- [ ] mypy type checking passes
- [ ] Tests passing with >90% coverage

---

### Phase 3: Integration Implementation

**Execute Phase 2 tasks from PRP:**

```bash
# Example: Integrating with existing components
# 1. Wire new feature into PluginRegistry / ToolRegistry
# 2. Add API endpoints if needed (FastAPI)
# 3. Create integration tests

touch tests/integration/test_[feature]_integration.py

# Run integration tests
pytest tests/integration/test_[feature]_integration.py -v
```

**Validation Checkpoint:**
```bash
# Run all SDK + integration tests
pytest tests/sdk/ tests/integration/ -v

# Check API endpoints (if added)
# Start server: uvicorn src.api:app --reload
# Test: curl http://localhost:8000/api/[feature]
```

**Checklist:**
- [ ] Integration with existing components complete
- [ ] API endpoints added (if needed)
- [ ] Integration tests passing
- [ ] No breaking changes to existing tests

---

### Phase 4: Full Validation Suite

**Run complete /validate command:**

```bash
# Phase 1: Code Quality
ruff format .
ruff check . --fix

# Phase 2: Type Safety
mypy src/ plugins/

# Phase 3: Tests
pytest tests/ -v --cov=src --cov=plugins --cov-report=term-missing

# Phase 4: Security
! grep -r "OPENAI" --include="*.py" src/ plugins/ || exit 1
! grep -r "sk-" --include="*.py" src/ plugins/ || exit 1  # No hardcoded keys

# Phase 5: Dependencies
pip check  # No broken dependencies

# Phase 6: Project Structure
test -f src/sdk/__init__.py
test -f tests/conftest.py
```

**Checklist:**
- [ ] Ruff format + check: PASS
- [ ] mypy type checking: PASS
- [ ] pytest (>90% coverage): PASS
- [ ] Security checks: PASS (no OpenAI, no hardcoded keys)
- [ ] Dependency check: PASS
- [ ] Project structure: PASS

---

### Phase 5: Documentation & Examples

**Update all documentation:**

```bash
# 1. Update CLAUDE.md
# Add new feature to "Current Status" or relevant section

# 2. Add docstrings
# All functions must have Google-style docstrings
"""
Short description.

Args:
    param1: Description
    param2: Description

Returns:
    Description of return value

Raises:
    ExceptionType: When this happens
"""

# 3. Create example
touch examples/[feature]_example.py

# 4. Update README if needed
```

**Validation Checkpoint:**
```bash
# Generate documentation (if using sphinx/mkdocs)
# Verify all docstrings present
ruff check --select D  # Docstring checks

# Test example code
python examples/[feature]_example.py
```

**Checklist:**
- [ ] CLAUDE.md updated with new feature
- [ ] All functions have docstrings
- [ ] Example code created and tested
- [ ] README.md updated (if needed)

---

### Phase 6: Review & Merge

**Final review before merge:**

```bash
# 1. Run FULL validation one more time
./scripts/validate.sh  # Or run /validate manually

# 2. Check git diff
git diff main...feature/[feature-name]

# 3. Verify no debug code left
! grep -r "print(" src/ || echo "WARNING: print statements found"
! grep -r "breakpoint()" src/ || echo "WARNING: breakpoints found"

# 4. Update TASK.md
echo "Completed: [feature-name] on $(date)" >> TASK.md

# 5. Commit with descriptive message
git add .
git commit -m "feat([component]): [feature-name]

- Implemented [key feature 1]
- Added tests with >90% coverage
- Updated documentation

Closes #[issue-number]"

# 6. Merge to main
git checkout main
git merge --no-ff feature/[feature-name]
git tag -a v0.1.x -m "Release: [feature-name]"
```

**Checklist:**
- [ ] All validation phases pass
- [ ] No debug code (print, breakpoint)
- [ ] TASK.md updated
- [ ] Git commit with descriptive message
- [ ] Merged to main (or PR created)
- [ ] Tagged release version

---

## Success Criteria

**All must be TRUE to complete execution:**

✅ **Code Quality**: Ruff format + check passes
✅ **Type Safety**: mypy passes with no errors
✅ **Tests**: >90% coverage, all passing
✅ **Security**: No OpenAI models, no hardcoded API keys
✅ **Documentation**: CLAUDE.md, docstrings, examples updated
✅ **Integration**: Works with existing conductor-ai components

---

## Critical Rules (Enforced at Each Phase)

- **NO OpenAI models** - Use DeepSeek, Qwen, Moonshot, Claude only
- **API keys in .env only** - Never hardcoded
- **Python 3.11+ features** - Type hints, match statements, async/await
- **Async-first** - All I/O operations async
- **TDD approach** - Write tests first, then implementation
- **>90% coverage** - Non-negotiable for all new code

---

## Troubleshooting

**Tests failing:**
```bash
# Run with verbose output
pytest tests/ -vv --tb=long

# Run specific test
pytest tests/test_[feature].py::test_function_name -vv
```

**Type errors:**
```bash
# Check specific file
mypy src/sdk/[new_feature].py --show-error-codes

# Ignore third-party typing issues (add to pyproject.toml)
```

**Coverage too low:**
```bash
# Find uncovered lines
pytest tests/ --cov=src --cov-report=html
open htmlcov/index.html  # View in browser
```
