"""Node definitions for Invoice Analyzer Agent."""
from framework.graph import NodeSpec


extract_items_node = NodeSpec(
    id="extract-items",
    name="Extract Line Items",
    description="Parse the invoice and extract all line items, fees, and charges",
    node_type="llm_generate",
    input_keys=["invoice_text"],
    output_keys=["line_items", "subtotal", "total", "tax_amount"],
    system_prompt="""\
You are an invoice parser. Extract ALL charges from the invoice, no matter how small or hidden.

For each line item, extract:
- description: what the charge is for
- amount: the dollar amount
- category: one of [product, service, tax, fee, shipping, discount, other]

IMPORTANT: Look carefully for:
- Small fees buried in the text
- Service charges
- Processing fees
- Administrative fees
- Convenience fees
- Handling charges
- Any percentage-based additions

CRITICAL: Return ONLY raw JSON. NO markdown, NO code blocks, NO ```json```.
Just the JSON object starting with { and ending with }

{"line_items": [{"description": "Item name", "amount": 10.00, "category": "product"}], "subtotal": 100.00, "total": 112.50, "tax_amount": 10.00}
""",
    tools=[],
    max_retries=3,
)


analyze_charges_node = NodeSpec(
    id="analyze-charges",
    name="Analyze Hidden Charges",
    description="Analyze extracted items to identify hidden or suspicious charges",
    node_type="llm_generate",
    input_keys=["line_items", "subtotal", "total", "tax_amount", "invoice_text"],
    output_keys=["hidden_charges", "warnings", "summary", "recommendation"],
    system_prompt="""\
You are a consumer protection analyst specializing in detecting hidden charges and deceptive billing practices.

Analyze the invoice line items and identify:

1. **Hidden Charges**: Fees that are:
   - Vaguely named (e.g., "service fee", "processing fee", "convenience fee")
   - Unusually high for what they cover
   - Not clearly explained
   - Percentage-based additions that seem excessive

2. **Red Flags**:
   - Charges that don't match the service/product
   - Duplicate charges
   - Fees that should be included in the base price
   - "Administrative" or "handling" fees
   - Automatic gratuity or service charges
   - Fuel surcharges, environmental fees
   - Charges with no clear description

3. **Math Check**:
   - Do the line items add up to the subtotal?
   - Is the tax calculated correctly?
   - Does subtotal + tax + fees = total?

CRITICAL: Return ONLY raw JSON. NO markdown, NO code blocks, NO ```json```.
Just the JSON object starting with { and ending with }

{"hidden_charges": [{"item": "Service Fee", "amount": 5.99, "concern": "Vague description", "severity": "medium"}], "warnings": ["warning"], "summary": "summary", "recommendation": "recommendation"}

Severity levels: "low", "medium", "high"
""",
    tools=[],
    max_retries=3,
)


__all__ = [
    "extract_items_node",
    "analyze_charges_node",
]
