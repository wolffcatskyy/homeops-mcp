# Contributing to HomeOps MCP

Thank you for your interest in contributing! Here are the guidelines to keep things smooth.

## Getting Started

1. Fork the repository and clone it locally.
2. Install dependencies: `poetry install`
3. Copy `.env.example` to `.env` and fill in any values you need for local testing.
4. Run the test suite to make sure everything passes before making changes.

## Development Workflow

1. **Create an issue first.** Use the AI-Ready issue templates in `.github/ISSUE_TEMPLATE/` when applicable.
2. **Branch from `main`.** Use a descriptive branch name, e.g. `feature/emby-sessions` or `fix/docker-timeout`.
3. **Write tests.** Every new adapter or endpoint needs unit tests with mocked external calls.
4. **Lint your code.** Run `poetry run ruff check .` and fix any issues before committing.
5. **Run the full test suite.** Run `poetry run pytest -v` to confirm nothing is broken.
6. **Open a pull request against `main`.** Describe what changed and why.

## Code Standards

- **Python 3.11+** -- use modern syntax (type hints, `match`, etc.).
- **Line length:** 100 characters max (configured in `pyproject.toml`).
- **Type hints** on all public function signatures.
- **Docstrings** on all public classes and functions.
- **Adapters are self-contained.** Each adapter lives in its own file under `homeops_mcp/adapters/` and should not depend on other adapters.

## Security Rules

- **No real credentials in code.** Ever. Not in tests, not in comments, not in examples.
- API keys and secrets go in `.env` (which is git-ignored).
- If you need example values, use obvious placeholders like `your_api_key_here`.
- Report security issues privately -- do not open a public issue.

## Issue Templates

We use structured, AI-Ready issue templates so that contributors (human and AI alike) have clear context. Please use them when filing new issues.

## Questions?

Open a discussion or reach out via an issue. We are happy to help.
