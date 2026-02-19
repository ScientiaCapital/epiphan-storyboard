# [Feature Name] - PRP Template

**Created**: YYYY-MM-DD
**Status**: Draft | In Progress | Review | Complete
**Owner**: [Developer Name]
**Project**: conductor-ai

---

## 1. Overview

### Problem Statement
**What problem does this solve?**

[Describe the problem or opportunity in 2-3 sentences. Be specific about the pain point or value proposition.]

### Success Criteria
- [ ] Functional requirement 1
- [ ] Functional requirement 2
- [ ] All tests passing (>90% coverage)
- [ ] Type checking passes (mypy)
- [ ] Code quality passes (ruff)
- [ ] No OpenAI models used
- [ ] API keys in .env only

---

## 2. Technical Design

### Architecture Overview
**How does this fit into conductor-ai architecture?**

```
┌─────────────────────────────────────────┐
│         CONDUCTOR-AI                     │
│  ┌──────────┐  ┌────────────┐           │
│  │ SDK      │  │ ToolRegistry│           │
│  │ (Public) │──│ (Global)   │           │
│  └──────────┘  └────────────┘           │
│        │              │                  │
│        ▼              ▼                  │
│  ┌──────────────────────────┐           │
│  │   [NEW FEATURE]          │           │
│  │   - Component A          │           │
│  │   - Component B          │           │
│  └──────────────────────────┘           │
│        │                                 │
│        ▼                                 │
│  ┌──────────┐  ┌──────────┐            │
│  │ Plugins  │  │ API      │            │
│  └──────────┘  └──────────┘            │
└─────────────────────────────────────────┘
```

### Component Breakdown

| Component | File Path | Changes | Est. LOC |
|-----------|-----------|---------|----------|
| SDK | `src/sdk/[new].py` | Create new module | 150 |
| Tools | `src/tools/[new].py` | Add new tool | 200 |
| Agents | `src/agents/[new].py` | Extend runner | 100 |
| API | `src/api.py` | Add endpoints | 50 |
| Tests | `tests/test_[new].py` | Unit tests | 300 |
| Docs | `CLAUDE.md` | Update status | 20 |

**Total Estimated LOC**: ~820

### Data Models

```python
from pydantic import BaseModel, Field

class FeatureInput(BaseModel):
    """Input schema for [feature]."""
    field1: str = Field(..., description="Description")
    field2: int = Field(ge=0, description="Description")

class FeatureOutput(BaseModel):
    """Output schema for [feature]."""
    result: dict
    execution_time_ms: float
    success: bool
```

### Dependencies

**New packages to add:**
```toml
# Add to pyproject.toml dependencies
"package-name>=1.0.0"
```

**Updated packages:**
```toml
# Upgrade existing
"existing-package>=2.0.0"  # was 1.5.0
```

**Removed packages:**
```toml
# None (or list deprecated dependencies)
```

---

## 3. Implementation Plan

### Phase 1: Foundation (Day 1)

**Goal**: Create base classes and unit tests

- [ ] **Task 1.1**: Create `src/sdk/[new_feature].py`
  - Base classes with type hints
  - Pydantic models for validation
  - Docstrings (Google style)

- [ ] **Task 1.2**: Write unit tests in `tests/test_[new_feature].py`
  - Test happy path
  - Test error cases
  - Test edge cases
  - Aim for >90% coverage

- [ ] **Task 1.3**: Run validation checkpoint
  - `ruff format . && ruff check . --fix`
  - `mypy src/sdk/[new_feature].py`
  - `pytest tests/test_[new_feature].py -v --cov`

**Exit Criteria**: Base classes working, tests passing, >90% coverage

---

### Phase 2: Integration (Day 2)

**Goal**: Integrate with existing conductor-ai components

- [ ] **Task 2.1**: Wire into PluginRegistry or ToolRegistry
  - Update `src/tools/registry.py` or `src/sdk/registry.py`
  - Add auto-discovery logic

- [ ] **Task 2.2**: Create integration tests
  - `tests/integration/test_[feature]_integration.py`
  - Mock external dependencies
  - Test end-to-end flow

- [ ] **Task 2.3**: Add API endpoints (if needed)
  - Update `src/api.py` with new routes
  - Add request/response schemas
  - Add endpoint tests

**Exit Criteria**: Integration complete, integration tests passing

---

### Phase 3: Polish & Documentation (Day 3)

**Goal**: Documentation, examples, final validation

- [ ] **Task 3.1**: Update documentation
  - Add to CLAUDE.md "Current Status" section
  - Add docstrings to all functions
  - Create `examples/[feature]_example.py`

- [ ] **Task 3.2**: Run full /validate command
  - All 6 phases must pass

- [ ] **Task 3.3**: Code review checklist
  - No debug code (print, breakpoint)
  - No hardcoded secrets
  - No OpenAI model references
  - All type hints present

**Exit Criteria**: All validation passes, docs updated, ready to merge

---

## 4. Testing Strategy

### Unit Tests (`tests/test_[feature].py`)

**Coverage Target**: >90%

**Key Test Scenarios**:
1. Happy path - normal operation
2. Invalid input - Pydantic validation errors
3. Error handling - exception cases
4. Edge cases - boundary conditions
5. Async behavior - concurrent operations

**Example Test Structure**:
```python
import pytest
from src.sdk.[new_feature] import FeatureClass

@pytest.mark.asyncio
async def test_feature_happy_path():
    """Test normal operation."""
    feature = FeatureClass(param="value")
    result = await feature.run()
    assert result.success is True

@pytest.mark.asyncio
async def test_feature_invalid_input():
    """Test validation errors."""
    with pytest.raises(ValidationError):
        FeatureClass(param=None)  # Missing required field
```

### Integration Tests (`tests/integration/test_[feature]_integration.py`)

**External Dependencies**:
- Mock: [List services to mock - Redis, Supabase, APIs]
- Real: [List services to use - none for unit tests]

**Example Integration Test**:
```python
@pytest.mark.asyncio
async def test_feature_with_registry():
    """Test integration with PluginRegistry."""
    registry = PluginRegistry()
    tool = registry.get_tool("feature_tool")
    result = await tool.run({"param": "value"})
    assert result.success is True
```

### Manual Testing

- [ ] Test scenario 1: [Describe manual test]
- [ ] Test scenario 2: [Describe manual test]
- [ ] Load test: [Performance requirements]

---

## 5. API Changes (If Applicable)

### New Endpoints

```python
# src/api.py

@app.post("/api/feature/action")
async def feature_action(request: FeatureRequest) -> FeatureResponse:
    """
    Execute feature action.

    Args:
        request: Feature input data

    Returns:
        FeatureResponse with result
    """
    pass

@app.get("/api/feature/{id}")
async def get_feature(id: str) -> FeatureResponse:
    """Get feature status by ID."""
    pass
```

### Request/Response Schemas

```python
class FeatureRequest(BaseModel):
    field1: str
    field2: int = Field(ge=0)

class FeatureResponse(BaseModel):
    id: str
    result: dict
    success: bool
    execution_time_ms: float
```

### Example API Usage

```bash
# Create
curl -X POST http://localhost:8000/api/feature/action \
  -H "Content-Type: application/json" \
  -d '{"field1": "value", "field2": 10}'

# Get
curl http://localhost:8000/api/feature/{id}
```

---

## 6. Documentation Updates

### CLAUDE.md Changes

**Section**: Current Status / [Relevant Section]

**Content to Add**:
```markdown
### [Feature Name] - COMPLETE
**Date**: YYYY-MM-DD
**Tests**: XX tests, >90% coverage

✅ **[Component Name]** (`src/[path]/`)
- Feature A - Description
- Feature B - Description
```

### Docstrings

**Style**: Google Style

**Example**:
```python
async def feature_function(param1: str, param2: int) -> FeatureResult:
    """
    Short description of what this does.

    Longer description with more detail if needed. Explain the purpose,
    behavior, and any important notes.

    Args:
        param1: Description of param1
        param2: Description of param2, must be >= 0

    Returns:
        FeatureResult containing:
            - result: Dict with output data
            - success: True if operation succeeded

    Raises:
        ValueError: If param2 is negative
        RuntimeError: If external service fails

    Example:
        >>> result = await feature_function("test", 10)
        >>> result.success
        True
    """
```

### Example Code

**File**: `examples/[feature]_example.py`

```python
"""
Example usage of [Feature Name].

This demonstrates how to use the new feature in conductor-ai.
"""

import asyncio
from src.sdk.[new_feature] import FeatureClass

async def main():
    """Run example."""
    feature = FeatureClass(param="value")
    result = await feature.run()
    print(f"Result: {result}")

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 7. Rollout Plan

### Prerequisites

- [ ] All tests passing (>90% coverage)
- [ ] Type checking passes (mypy)
- [ ] Code quality passes (ruff)
- [ ] Security checks pass (no OpenAI, no hardcoded keys)
- [ ] Documentation updated (CLAUDE.md, docstrings, examples)
- [ ] Code reviewed by [Reviewer Name]

### Deployment Steps

1. **Merge to main branch**
   ```bash
   git checkout main
   git merge --no-ff feature/[feature-name]
   ```

2. **Tag release version**
   ```bash
   git tag -a v0.1.x -m "Release: [Feature Name]"
   git push origin main --tags
   ```

3. **Update docker-compose.yml** (if needed)
   - Add new environment variables
   - Update service configurations

4. **Deploy to staging**
   - Test in staging environment
   - Monitor logs for errors

5. **Deploy to production**
   - Gradual rollout if applicable
   - Monitor metrics

---

## 8. Risks & Mitigations

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Breaking change to existing SDK | Low | High | Maintain backward compatibility, version SDK exports |
| Performance regression | Medium | Medium | Add benchmarks, profile before/after |
| External API failure | Medium | High | Add retry logic with tenacity, circuit breaker |
| Model provider rate limits | Medium | Medium | Use DeepSeek/Qwen (cheap), add exponential backoff |

---

## 9. Success Metrics

### Code Quality
- [ ] Ruff format + check: PASS
- [ ] mypy type checking: PASS (0 errors)
- [ ] Test coverage: >90% (target: 95%+)
- [ ] pytest: All tests passing

### Security
- [ ] No OpenAI model references
- [ ] No hardcoded API keys (all in .env)
- [ ] No secrets in git history

### Performance
- [ ] Endpoint response time: <500ms (p95)
- [ ] Tool execution time: <3000ms (p95)
- [ ] Memory usage: <200MB per request

### Documentation
- [ ] CLAUDE.md updated
- [ ] All functions have docstrings
- [ ] Example code works
- [ ] README.md updated (if needed)

---

## 10. Final Checklist

**Before marking PRP as Complete:**

- [ ] Code written and tested locally
- [ ] /validate passes all 6 phases
- [ ] CLAUDE.md updated with feature status
- [ ] Tests added with >90% coverage
- [ ] Type hints on all functions
- [ ] Docstrings (Google style) on all public functions
- [ ] Example code created and tested
- [ ] No OpenAI models used (DeepSeek/Qwen/Claude only)
- [ ] No API keys hardcoded (all in .env)
- [ ] Git commit with descriptive message
- [ ] Merged to main or PR created
- [ ] TASK.md updated with completion status

---

## Notes

[Any additional notes, learnings, or future improvements]

---

**Template Version**: 1.0 (conductor-ai)
**Last Updated**: 2025-11-30
