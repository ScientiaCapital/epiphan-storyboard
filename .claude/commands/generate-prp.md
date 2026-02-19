# Generate PRP (Planning & Review Protocol)

Create a comprehensive implementation plan following conductor-ai project standards.

## Usage

```
/generate-prp [feature-name]
```

## Process

### 1. Analyze Requirements
- Read CLAUDE.md for project context and current status
- Check existing code structure in src/, plugins/, tests/
- Review pyproject.toml for dependencies and tooling
- Identify affected components (SDK, tools, agents, API)

### 2. Create PRP Document

Generate `PRPs/[feature-name]-[YYYYMMDD].md` with:

```markdown
# [Feature Name] - PRP

**Created**: YYYY-MM-DD
**Status**: Draft
**Owner**: [Developer Name]

## 1. Overview

### Problem Statement
[What problem does this solve?]

### Success Criteria
- [ ] Criterion 1
- [ ] Criterion 2
- [ ] All tests passing (>90% coverage)
- [ ] Type checking passes (mypy)
- [ ] Code quality passes (ruff)
- [ ] No OpenAI models used

## 2. Technical Design

### Architecture Changes
[How does this fit into conductor-ai architecture?]

### Component Breakdown
| Component | Changes | Estimated LOC |
|-----------|---------|---------------|
| src/sdk/  | ... | ... |
| src/tools/ | ... | ... |
| src/agents/ | ... | ... |
| plugins/ | ... | ... |
| tests/ | ... | ... |

### Dependencies
- New: [packages to add]
- Updated: [packages to upgrade]
- Removed: [packages to remove]

## 3. Implementation Plan

### Phase 1: Foundation (Day 1)
- [ ] Task 1.1: Create base classes/functions
- [ ] Task 1.2: Add type hints
- [ ] Task 1.3: Write unit tests

### Phase 2: Integration (Day 2)
- [ ] Task 2.1: Integrate with existing components
- [ ] Task 2.2: Add integration tests
- [ ] Task 2.3: Update API endpoints (if needed)

### Phase 3: Validation (Day 3)
- [ ] Task 3.1: Run /validate command
- [ ] Task 3.2: Fix any issues
- [ ] Task 3.3: Update documentation

## 4. Testing Strategy

### Unit Tests
- Test file: `tests/test_[feature].py`
- Coverage target: >90%
- Key scenarios: [list]

### Integration Tests
- Test file: `tests/integration/test_[feature].py`
- External dependencies: [mocked services]

### Manual Testing
- [ ] Test case 1
- [ ] Test case 2

## 5. API Changes (if applicable)

### New Endpoints
```python
POST /api/[feature]/action
GET /api/[feature]/{id}
```

### Request/Response Schemas
```python
class FeatureRequest(BaseModel):
    field: str

class FeatureResponse(BaseModel):
    result: dict
```

## 6. Documentation Updates

- [ ] Update CLAUDE.md with new feature
- [ ] Add docstrings to all functions
- [ ] Update README.md if needed
- [ ] Create example in examples/ directory

## 7. Rollout Plan

### Prerequisites
- [ ] All tests passing
- [ ] Code reviewed
- [ ] Documentation updated

### Deployment Steps
1. Merge to main branch
2. Tag release version
3. Update docker-compose.yml if needed
4. Deploy to staging/production

## 8. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Risk 1 | High | Mitigation strategy |

## 9. Success Metrics

- [ ] Tests: >90% coverage, all passing
- [ ] Performance: [metrics]
- [ ] Quality: ruff + mypy passing
- [ ] No OpenAI model usage

## 10. Checklist

- [ ] Code written and tested
- [ ] /validate passes all phases
- [ ] CLAUDE.md updated
- [ ] Tests added (>90% coverage)
- [ ] Type hints complete
- [ ] Documentation updated
- [ ] No OpenAI models used
- [ ] API keys in .env only
```

## 3. Review Against Standards

### Conductor-AI Standards
- ✅ **SDK-first design**: 5 imports only (BaseTool, ToolCategory, ToolDefinition, ToolResult, PluginRegistry)
- ✅ **Model selection**: Use DeepSeek V3, DeepSeek R1, Qwen3-235B, Kimi K2, or Claude
- ✅ **Async patterns**: All I/O operations use async/await
- ✅ **Plugin system**: Tools auto-discovered from plugins/ directory
- ✅ **Audit logging**: Use @audit_logged decorator for observability
- ✅ **Testing**: pytest with >90% coverage

### Python Best Practices
- ✅ Python 3.11+ features (type hints, match statements)
- ✅ Ruff for linting and formatting
- ✅ mypy for type checking
- ✅ Pydantic v2 for validation
- ✅ SQLAlchemy 2.0 async patterns

## 4. Save and Track

```bash
# Save PRP
git add PRPs/[feature-name]-[YYYYMMDD].md

# Create tracking branch
git checkout -b feature/[feature-name]

# Update TASK.md
echo "Current: Implementing [feature-name] (see PRPs/[feature-name]-[YYYYMMDD].md)" >> TASK.md
```

## Example PRP Names

- `plugin-integration-vozlux-20251130.md`
- `tool-web-scraper-upgrade-20251130.md`
- `sdk-retry-logic-20251130.md`
- `api-batch-execution-20251130.md`
