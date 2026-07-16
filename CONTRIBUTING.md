<!-- How to set up a dev environment, run checks, and submit pull requests. -->
# Contributing to PC Phone Link

Thank you for your interest in improving PC Phone Link.

## Development setup

See [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) for environment setup and run commands.

Quick start:

```powershell
cd "c:\PC Phone Link"
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python run_phone_link.py --host 0.0.0.0 --port 8765
```

## Before submitting a pull request

1. **Python syntax** — `python -m compileall phone_link`
2. **JavaScript syntax** — `node --check phone_link/static/app.js`
3. **Manual smoke test** — Pair a phone browser, pick a window, verify streaming and input
4. **Keep changes focused** — One logical change per pull request

## Code style

- Match existing naming and structure in the file you edit
- Prefer small, readable changes over large refactors
- Only add comments for non-obvious behavior
- Windows-only APIs belong in `phone_link/windows_host.py` and related modules

## Pull request expectations

- Describe what changed and why
- Link related issues when applicable
- Include screenshots or screen recordings for UI changes
- Note any new ports, env vars, or setup steps in the README or docs

## Reporting bugs

Use the [bug report template](.github/ISSUE_TEMPLATE/bug_report.yml) and include:

- Windows version
- How you run the app (Release `.exe` vs Python)
- Steps to reproduce
- Relevant log excerpts from `%LOCALAPPDATA%\PC Phone Link\logs\`

## Feature requests

Use the [feature request template](.github/ISSUE_TEMPLATE/feature_request.yml).

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
