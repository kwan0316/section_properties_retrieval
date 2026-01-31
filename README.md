# UC/UB Steel Section Lookup

Prereqs
- Python 3.8+
- The two Excel files must be next to the script:
  - `UC-secpropsdimsprops-EC3UKNA-UK-1-31-2026.xlsx`
  - `UB-secpropsdimsprops-EC3UKNA-UK-1-31-2026.xlsx`

Quick setup (PowerShell)
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Run built-in tests
```powershell
.\.venv\Scripts\Activate.ps1; python uc_ub_data_retrieval.py
```

Interactive lookup
```powershell
.\.venv\Scripts\Activate.ps1; python -c "import uc_ub_data_retrieval as m; m.interactive_test()"
```

Run as FastAPI server
```powershell
.\.venv\Scripts\Activate.ps1; uvicorn uc_ub_data_retrieval:create_fastapi_app --factory --reload --host 127.0.0.1 --port 8000
```

API example
- GET /section/{input_string}
- Example: `http://127.0.0.1:8000/section/uc%20356x406x1299`

Lookup format
- Use two-dimension section designations (depth x width). Examples:
  - `uc 356x406`
  - `ub 1016x305`
  (The test strings with a third number, e.g. `356x406x1299`, will not match the current data.)

Now accepted formats
- You can include a comma after the type or use a space. Examples:
  - `uc, 356x406x1299`
  - `ub 914x305x576`
  - `ub,914x305x576`

Column names
- Several previously `Unnamed:` columns are renamed on load (e.g. `Unnamed: 7` → `Flange thickness (tf)`, `Unnamed: 18` → `Izz (cm4)`). This improves property keys returned by lookups.
