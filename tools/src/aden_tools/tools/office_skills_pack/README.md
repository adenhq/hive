# Office Skills Pack (MVP)

Schema-first, local generation of business artifacts:

- Excel: `.xlsx` (multi-sheet + formatting via openpyxl)
- PowerPoint: `.pptx` (title + bullets + optional images via python-pptx)
- Word: `.docx` (sections + bullets + tables via python-docx)
- Charts: `.png` (matplotlib)

## Install
From `tools/`:

```bash
python -m pip install -e ".[excel,word,powerpoint,charts]"
```

## Contract
All tools return:

- `success: bool`
- `output_path: str | null`
- `contract_version: "0.1.0"`
- `error: { code, message, details } | null`
- `metadata: {...}`

## Error codes
- `INVALID_PATH`
- `INVALID_SCHEMA`
- `DEP_MISSING`
- `IO_ERROR`
- `UNKNOWN`

Example error payload:

```json
{
  "success": false,
  "output_path": null,
  "contract_version": "0.1.0",
  "error": {
    "code": "INVALID_SCHEMA",
    "message": "Invalid workbook schema",
    "details": "..."
  },
  "metadata": {}
}
```

## Charts
Generate PNG using `chart_render_png`, then embed into:

- PPTX via `powerpoint_generate` (`image_paths` / `charts`)
- XLSX via `excel_write` (`sheets[].images`)
- DOCX via `word_generate` (`sections[].image_paths` / `sections[].charts`)

## Demo
From repo root:

```bash
python tools/examples/office_skills_pack_demo.py
```

## Example payloads
See `tools/tests/fixtures/office_skills_pack/` for sample JSON inputs.
