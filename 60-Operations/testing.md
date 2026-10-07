# Testing Runbook

From the repository root:

```bash
cd 50-Code
python -m venv .venv
.\.venv\Scripts\Activate.ps1   # Windows PowerShell
pip install -r requirements.txt
python -m pytest tests/ -v
```

On Linux/macOS activate with `source .venv/bin/activate`.

## Coverage

The repository enforces an initial **80% minimum branch-coverage floor**. Run the same coverage gate locally with:

```bash
python -m pytest tests/ -v --cov=dealfinder --cov-branch --cov-report=term-missing --cov-report=xml:coverage.xml --cov-fail-under=80
```

GitHub Actions runs this command on every push and pull request and uploads `coverage.xml` as a workflow artifact.

A change is not considered complete until the relevant tests pass. Run the full suite before merging changes that affect core calculation, evaluation, scoring, persistence, matching, valuation, or connectors.
