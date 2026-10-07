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

A change is not considered complete until the relevant tests pass. Run the full suite before merging changes that affect core calculation, evaluation, scoring, persistence, matching, valuation, or connectors.
