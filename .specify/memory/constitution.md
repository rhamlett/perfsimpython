<!--
  ============================================================================
  SYNC IMPACT REPORT
  ============================================================================
  Version change: N/A (initial) → 1.0.0
  
  Modified Principles: None (initial creation)
  
  Added Sections:
    - Core Principles (5 principles)
    - Code Quality Standards
    - Technology Standards (including Source Control, Python, Code Quality Tools, 
      Framework Standards, Documentation Standards, UI Design Standards)
    - Development Workflow
    - Governance
  
  Removed Sections: None (initial creation)
  
  Templates Status:
    - plan-template.md: ✅ Compatible (Constitution Check section present)
    - spec-template.md: ✅ Compatible (Requirements align with principles)
    - tasks-template.md: ✅ Compatible (Phase structure supports TDD)
  
  UI Design Consistency:
    - Python version MUST match visual design of Node.js and .NET Core versions
    - Shared components: header, sidebar drawer, side panel, metric tiles, charts
    - Reference: PerfSimNode, PerfProblemSimulator-NETCore repositories
  
  Follow-up TODOs: None
  ============================================================================
-->

# PythonApp Constitution

## Core Principles

### I. Code Quality & Readability

All code MUST prioritize clarity, maintainability, and correctness over brevity or cleverness.

**Non-negotiable rules:**

- Every module, class, and public function MUST include docstrings following Google or NumPy style
- Documentation MUST explain the "why" (intent and rationale), not just the "what" (behavior)
- Code MUST be written to assist learning developers in understanding patterns and decisions
- Complex logic MUST include inline comments explaining the approach in broad terms
- Naming MUST be descriptive and self-documenting; follow PEP 8 naming conventions
- No magic numbers or hardcoded strings; use constants with descriptive names
- Single responsibility principle: each function/class should do one thing well

**Rationale:** Code is read far more often than it is written. Clear, well-documented code reduces onboarding time, prevents bugs, and enables confident refactoring.

### II. Documentation-First

All public interfaces MUST be documented before implementation.

**Non-negotiable rules:**

- Docstrings MUST be present for all modules, classes, and public functions
- README files MUST exist at the project root and for significant modules
- API endpoints MUST be documented with OpenAPI/Swagger specifications
- Configuration options MUST be documented with valid values and effects
- Complex algorithms MUST include step-by-step explanations

**Rationale:** Documentation enables maintainability, knowledge transfer, and proper API usage. It forces clarity of thought during design.

### III. Test-Driven Development (Encouraged)

Tests SHOULD be written before or alongside implementation code.

**Guidelines:**

- Write test cases covering acceptance criteria before implementation when practical
- Follow the Arrange-Act-Assert pattern for test structure
- Unit tests MUST cover all public interfaces
- Integration tests SHOULD verify cross-component interactions
- Test naming convention: `test_<function_name>_<scenario>_<expected_behavior>`

**Testing Standards:**

- Minimum 80% code coverage for business logic
- Integration tests required for all external integrations
- Use pytest as the testing framework
- Mock external dependencies appropriately

**Rationale:** TDD ensures code meets requirements from the start, produces better-designed interfaces, and creates a safety net for future changes.

### IV. Simplicity & YAGNI

Code MUST solve the current requirement without over-engineering for hypothetical future needs.

**Non-negotiable rules:**

- Implement only what is explicitly required; no speculative features
- Prefer composition over inheritance
- Avoid premature optimization; measure before optimizing
- Choose the simplest solution that meets requirements
- Complexity MUST be justified in code comments or design documents
- Minimize external dependencies; prefer standard library when possible

**Rationale:** Unnecessary complexity increases maintenance burden, introduces bugs, and makes code harder to understand. Simple code is easier to test, debug, and extend.

### V. Defensive Programming

Code MUST anticipate and handle error conditions gracefully.

**Non-negotiable rules:**

- All public function parameters MUST be validated; use guard clauses at function entry
- Exceptions MUST be caught at appropriate boundaries with meaningful error messages
- Use type hints throughout the codebase for clarity and static analysis
- All external calls (APIs, database, file I/O) MUST include appropriate error handling
- Logging MUST capture sufficient context for debugging production issues
- Use Python's logging module; avoid print statements for production code

**Rationale:** Defensive code fails predictably and provides actionable information when things go wrong, reducing debugging time and improving user experience.

## Technology Standards

### Source Control & CI/CD

- **Repository**: https://github.com/rhamlett/perfsimpython
- **Primary Branch**: `main`
- **CI/CD**: GitHub Actions with OIDC authentication to Azure
- **Branch Protection**: Required for `main` branch (PR reviews, passing checks)
- **Commit Messages**: Use conventional commits format when practical

### Python Version & Environment

- **Version**: Python 3.11+ (use latest stable LTS features)
- **Virtual Environment**: Required; use venv or poetry
- **Package Management**: pip with requirements.txt or poetry with pyproject.toml
- **Type Hints**: Required for all public interfaces; use mypy for static analysis

### Code Quality Tools

| Tool | Purpose | Configuration |
|------|---------|---------------|
| Black | Code formatting | Default settings (line length 88) |
| Ruff or Flake8 | Linting | Configured in pyproject.toml |
| mypy | Type checking | Strict mode for new code |
| pytest | Testing | With pytest-cov for coverage |
| isort | Import sorting | Compatible with Black |

### Framework Standards

- **Web Framework**: FastAPI (preferred) or Flask
- **ASGI Server**: Uvicorn for production
- **Async Support**: Use async/await for I/O-bound operations
- **Validation**: Pydantic for request/response models
- **Real-time**: WebSockets via FastAPI or python-socketio

### Documentation Standards

| Element | Documentation Required |
|---------|----------------------|
| Modules | Module-level docstring describing purpose |
| Classes | Class docstring with usage examples when helpful |
| Public functions | Docstring with Args, Returns, Raises sections |
| Complex algorithms | Inline comments explaining the approach |
| Configuration | Comments explaining valid values and effects |
| Constants | Descriptive names; comments if purpose not obvious |

### UI Design Standards

This application is part of the Performance Problem Simulator family, which includes Node.js and
.NET Core versions. The Python version MUST maintain visual consistency with these applications.

**Non-negotiable rules:**

- Dashboard MUST use the shared component design (header, sidebar drawer, side panel, metric tiles)
- CSS MUST use CSS variables for theming (colors, shadows, radii, transitions)
- Font family MUST be 'Segoe UI' with system font fallbacks
- All pages MUST include the shared left sidebar navigation drawer
- Simulation controls MUST appear in a right slide-out panel
- Styling MUST be vanilla CSS (no CSS frameworks like Bootstrap or Tailwind)
- JavaScript MUST be vanilla JS (no frontend frameworks like React or Vue)

**Shared Components:**

| Component | Purpose |
|-----------|---------|
| Header | Fixed, contains hamburger menu, title, SKU badge, panel toggle, connection status |
| Sidebar Drawer | Left slide-out navigation with links to all pages and GitHub |
| Side Panel | Right slide-out panel containing simulation controls |
| Metric Tiles | Cards showing real-time metrics with progress bars |
| Chart Cards | Chart.js visualizations for trends |
| Event Log | Scrollable timestamped event list |

**Reference Implementations:**
- Node.js: https://github.com/rhamlett/PerfSimNode
- .NET Core: https://github.com/rhamlett/PerfProblemSimulator-NETCore

## Development Workflow

### Feature Implementation Process

1. **Specification:** Define requirements and acceptance criteria in `/specs/`
2. **Planning:** Create implementation plan with Constitution Check gate
3. **Test Writing:** Write failing tests covering all acceptance criteria
4. **Implementation:** Write code to pass tests, following principles above
5. **Refactoring:** Clean up while maintaining passing tests
6. **Review:** Verify compliance with this constitution before merge

### Quality Gates

Before any PR can be merged:

- [ ] All tests pass (pytest) - enforced by GitHub Actions
- [ ] Code coverage meets thresholds (80%+ for business logic)
- [ ] Linting passes (ruff/flake8) - enforced by GitHub Actions
- [ ] Type checking passes (mypy) - enforced by GitHub Actions
- [ ] Code is formatted (black, isort) - enforced by GitHub Actions
- [ ] Documentation is complete
- [ ] Constitution Check in plan.md shows no violations
- [ ] GitHub Actions workflow completes successfully

### Code Review Checklist

All code reviews MUST verify:

- [ ] Docstrings are complete and meaningful
- [ ] Tests exist and follow testing standards
- [ ] Error handling is comprehensive
- [ ] Type hints are present and accurate
- [ ] No code smells (long functions, large classes, duplicate code)
- [ ] Naming is clear and follows PEP 8
- [ ] Logging is appropriate for production debugging

## Governance

This constitution supersedes all other development practices for this project.

### Amendment Process

1. Proposed changes MUST be documented with rationale
2. Changes MUST be reviewed by project stakeholders
3. Version number MUST be incremented according to semantic versioning:
   - **MAJOR:** Removing principles or backward-incompatible governance changes
   - **MINOR:** Adding new principles or materially expanding guidance
   - **PATCH:** Clarifications, wording improvements, non-semantic refinements
4. All affected templates and documentation MUST be updated to reflect changes

### Compliance

- All pull requests MUST include a Constitution Check section confirming compliance
- Violations MUST be documented and justified if proceeding
- Repeated violations warrant process review and potential team discussion

**Version**: 1.0.0 | **Ratified**: 2026-03-13 | **Last Amended**: 2026-03-13
