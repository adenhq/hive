# Invoice Analyzer Agent

Analyzes invoices to detect hidden charges, unusual fees, and potential overcharges.

## What It Does

Takes invoice text (or PDF/image via OCR) and identifies:
- Hidden fees with vague descriptions
- Service charges and processing fees
- Unusual or excessive charges
- Math errors in totals

## Flow

```
[invoice_text] --> parse-request --> generate-sql --> [sql, explanation]
```

Two nodes:
1. **extract-items**: Parses invoice, extracts all line items
2. **analyze-charges**: Identifies suspicious charges, generates warnings

## Usage

```bash
# Set up (if using cloud LLM)
export GOOGLE_API_KEY="..."  # or OPENAI_API_KEY, etc.

# Run with text
PYTHONPATH=core:exports python -m invoice_analyzer_agent run --text "INVOICE #123..."

# Run with file (supports .txt, .pdf, .png, .jpg)
PYTHONPATH=core:exports python -m invoice_analyzer_agent run --file invoice.pdf

# Run demo
PYTHONPATH=core:exports python -m invoice_analyzer_agent demo
```

## Example Output

```
HIDDEN CHARGES DETECTED:

  [HIGH] Service Charge - $64.44
     Vague description - unclear what service this covers

  [MEDIUM] Platform Fee - $19.99
     Fee that should be included in base price

SUMMARY:
  Invoice contains 4 suspicious fees totaling $95.71

RECOMMENDATION:
  Contact vendor to clarify fee descriptions before paying
```

## Configuration

Edit `config.py` to change the model:

```python
model: str = "ollama/llama3.2"      # Free, local, slow
model: str = "gemini/gemini-2.0-flash"  # Free tier, fast
model: str = "gpt-4o-mini"          # Paid, fast, high quality
```

## Customization

Edit `nodes/__init__.py` to:
- Add more fee patterns to detect
- Change severity thresholds
- Add industry-specific rules (telecom, restaurant, SaaS, etc.)
