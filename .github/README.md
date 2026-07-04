# `.github`

GitHub configuration for this repository.

| Path | Purpose |
| ---- | ------- |
| [`workflows/ci.yml`](workflows/ci.yml) | Runs on every push and pull request — Python syntax checks, JavaScript syntax checks, and an Android debug build |
| [`workflows/release.yml`](workflows/release.yml) | Builds Windows `.exe` bundles and a source zip when a version tag such as `v1.0.0` is pushed |
| [`ISSUE_TEMPLATE/`](ISSUE_TEMPLATE/) | Structured forms for bug reports and feature requests |
| [`pull_request_template.md`](pull_request_template.md) | Checklist and prompts for pull request authors |
