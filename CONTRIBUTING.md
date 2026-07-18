# Contributing to SpineSpy

Thanks for your interest in contributing! Here's how to get started.

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/YOUR_USERNAME/spinespy.git`
3. Install Poetry 2.3 or newer
4. Install locked dependencies: `poetry install --with dev`
5. Download verified models: `./scripts/download_models.sh`

## Making Changes

1. Create a feature branch: `git checkout -b feature/your-feature-name`
2. Make your changes
3. Run the automated tests: `poetry run pytest -q`
4. Test the app locally when behavior changes: `poetry run start`
5. Commit with a clear message: `git commit -m "feat: add your feature"`

## Commit Messages

Use conventional commits:
- `feat:` new feature
- `fix:` bug fix
- `docs:` documentation changes
- `refactor:` code refactoring

## Pull Requests

1. Push to your fork: `git push origin feature/your-feature-name`
2. Open a PR against `main`
3. Fill out the PR template
4. Wait for review

## Reporting Bugs

Open an issue using the bug report template. Include:
- macOS version
- Python version
- Steps to reproduce
- Expected vs actual behavior

## Questions?

Open a discussion or issue - we're happy to help!
