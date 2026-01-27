"""CLI for Invoice Analyzer Agent."""

import asyncio
import json
import sys
from pathlib import Path
import click

from .agent import default_agent


def extract_text_from_file(filepath: str) -> str:
    """Extract text from various file formats (txt, pdf, png, jpg)."""
    path = Path(filepath)
    suffix = path.suffix.lower()

    # Plain text
    if suffix in ['.txt', '.text', '.md']:
        with open(filepath, 'r') as f:
            return f.read()

    # PDF
    elif suffix == '.pdf':
        try:
            from pypdf import PdfReader
            reader = PdfReader(filepath)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
            return text.strip()
        except ImportError:
            raise click.ClickException("PDF support requires pypdf: pip install pypdf")

    # Images (PNG, JPG, JPEG)
    elif suffix in ['.png', '.jpg', '.jpeg', '.tiff', '.bmp']:
        try:
            import pytesseract
            from PIL import Image
            img = Image.open(filepath)
            text = pytesseract.image_to_string(img)
            return text.strip()
        except ImportError:
            raise click.ClickException(
                "Image OCR requires pytesseract and Pillow:\n"
                "  pip install pytesseract Pillow\n"
                "  brew install tesseract  # macOS"
            )
        except Exception as e:
            if "tesseract" in str(e).lower():
                raise click.ClickException(
                    "Tesseract OCR not found. Install it:\n"
                    "  macOS: brew install tesseract\n"
                    "  Ubuntu: sudo apt install tesseract-ocr"
                )
            raise

    else:
        raise click.ClickException(f"Unsupported file format: {suffix}")


@click.group()
@click.version_option(version="1.0.0")
def cli():
    """Invoice Analyzer - Detect hidden charges in invoices."""
    pass


@cli.command()
@click.option("--text", "-t", type=str, help="Invoice text to analyze")
@click.option("--file", "-f", type=click.Path(exists=True), help="File containing invoice (txt, pdf, png, jpg)")
@click.option("--verbose", "-v", is_flag=True, help="Show execution details")
@click.option("--json-output", "-j", is_flag=True, help="Output as JSON")
def run(text, file, verbose, json_output):
    """Analyze an invoice for hidden charges."""
    import logging

    if verbose:
        logging.basicConfig(level=logging.INFO, format='%(message)s')

    if file:
        text = extract_text_from_file(file)

    if not text:
        click.echo("Error: Provide invoice via --text or --file", err=True)
        sys.exit(1)

    context = {"invoice_text": text}

    if not json_output:
        click.echo("=" * 50)
        click.echo("INVOICE ANALYZER")
        click.echo("=" * 50)
        click.echo(f"\nAnalyzing invoice ({len(text)} chars)...\n")

    result = asyncio.run(default_agent.run(context))

    if json_output:
        output = {"success": result.success, "output": result.output}
        if result.error:
            output["error"] = result.error
        click.echo(json.dumps(output, indent=2, default=str))
    else:
        if result.success:
            click.echo("=" * 50)
            click.echo("ANALYSIS RESULTS")
            click.echo("=" * 50)

            # Show hidden charges
            if "hidden_charges" in result.output:
                charges = result.output["hidden_charges"]
                if charges:
                    click.echo("\n🚨 HIDDEN CHARGES DETECTED:\n")
                    for charge in charges:
                        severity_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(charge.get("severity", ""), "⚪")
                        click.echo(f"  {severity_emoji} {charge.get('item', 'Unknown')} - ${charge.get('amount', 0):.2f}")
                        click.echo(f"     └─ {charge.get('concern', 'No details')}\n")
                else:
                    click.echo("\n✅ No hidden charges detected!\n")

            # Show warnings
            if "warnings" in result.output and result.output["warnings"]:
                click.echo("⚠️  WARNINGS:")
                for warning in result.output["warnings"]:
                    click.echo(f"  • {warning}")
                click.echo()

            # Show summary
            if "summary" in result.output:
                click.echo("📋 SUMMARY:")
                click.echo(f"  {result.output['summary']}\n")

            # Show recommendation
            if "recommendation" in result.output:
                click.echo("💡 RECOMMENDATION:")
                click.echo(f"  {result.output['recommendation']}\n")

            # Show line items if verbose
            if verbose and "line_items" in result.output:
                click.echo("\n📝 EXTRACTED LINE ITEMS:")
                for item in result.output["line_items"]:
                    click.echo(f"  • {item.get('description', 'Unknown')}: ${item.get('amount', 0):.2f} [{item.get('category', '')}]")

        else:
            click.echo(f"\n❌ Analysis failed: {result.error}", err=True)

    sys.exit(0 if result.success else 1)


@cli.command()
@click.option("--json", "output_json", is_flag=True)
def info(output_json):
    """Show agent information."""
    info_data = default_agent.info()
    if output_json:
        click.echo(json.dumps(info_data, indent=2))
    else:
        click.echo(f"Agent: {info_data['name']}")
        click.echo(f"Version: {info_data['version']}")
        click.echo(f"Description: {info_data['description']}")
        click.echo(f"\nFlow: {' -> '.join(info_data['nodes'])}")


@cli.command()
def validate():
    """Validate agent structure."""
    validation = default_agent.validate()
    if validation["valid"]:
        click.echo("✅ Agent is valid")
    else:
        click.echo("❌ Agent has errors:")
        for error in validation["errors"]:
            click.echo(f"  {error}")
    sys.exit(0 if validation["valid"] else 1)


@cli.command()
def demo():
    """Run with a sample invoice."""
    sample_invoice = """
    INVOICE #12345
    Date: January 25, 2025

    Cloud Services Inc.

    Description                          Amount
    ----------------------------------------
    Monthly Subscription (Pro Plan)     $49.99
    Additional Storage (50GB)           $10.00
    API Calls (10,000)                  $15.00

    Subtotal                            $74.99

    Service Fee                          $4.99
    Platform Fee                         $2.99
    Processing Fee                       $1.50
    Environmental Compliance Fee         $0.75

    Tax (8.5%)                          $7.18

    TOTAL                              $92.40

    * Service fee covers account maintenance
    * Platform fee is non-refundable
    """

    click.echo("Running demo with sample invoice...\n")
    context = {"invoice_text": sample_invoice}
    result = asyncio.run(default_agent.run(context))

    if result.success:
        click.echo("=" * 50)
        click.echo("DEMO RESULTS")
        click.echo("=" * 50)

        if "hidden_charges" in result.output:
            charges = result.output["hidden_charges"]
            if charges:
                click.echo("\n🚨 HIDDEN CHARGES FOUND:\n")
                for charge in charges:
                    severity_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(charge.get("severity", ""), "⚪")
                    click.echo(f"  {severity_emoji} {charge.get('item', 'Unknown')} - ${charge.get('amount', 0):.2f}")
                    click.echo(f"     └─ {charge.get('concern', '')}\n")

        if "summary" in result.output:
            click.echo(f"📋 {result.output['summary']}\n")

        if "recommendation" in result.output:
            click.echo(f"💡 {result.output['recommendation']}\n")
    else:
        click.echo(f"❌ Demo failed: {result.error}")


if __name__ == "__main__":
    cli()
