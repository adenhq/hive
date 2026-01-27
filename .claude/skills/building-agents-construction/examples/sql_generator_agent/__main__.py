"""CLI for SQL Generator Agent."""

import asyncio
import json
import sys
import click

from .agent import default_agent


@click.group()
@click.version_option(version="1.0.0")
def cli():
    """SQL Generator - Convert natural language to SQL."""
    pass


@cli.command()
@click.option("--question", "-q", type=str, required=True, help="Natural language question")
@click.option("--schema", "-s", type=str, required=True, help="Database schema (or path to .sql file)")
@click.option("--verbose", "-v", is_flag=True, help="Show execution details")
@click.option("--json-output", "-j", is_flag=True, help="Output as JSON")
def run(question, schema, verbose, json_output):
    """Generate SQL from natural language."""
    import logging
    from pathlib import Path

    if verbose:
        logging.basicConfig(level=logging.INFO, format='%(message)s')

    # If schema is a file path, read it
    if Path(schema).exists():
        with open(schema, 'r') as f:
            schema = f.read()

    context = {"question": question, "schema": schema}

    if not json_output:
        click.echo("=" * 50)
        click.echo("SQL GENERATOR")
        click.echo("=" * 50)
        click.echo(f"\nQuestion: {question}")
        click.echo(f"Schema: {schema[:100]}..." if len(schema) > 100 else f"Schema: {schema}")
        click.echo("\nGenerating SQL...\n")

    result = asyncio.run(default_agent.run(context))

    if json_output:
        output = {"success": result.success, "output": result.output}
        if result.error:
            output["error"] = result.error
        click.echo(json.dumps(output, indent=2, default=str))
    else:
        if result.success:
            click.echo("=" * 50)
            click.echo("RESULT")
            click.echo("=" * 50)

            if "sql" in result.output:
                click.echo("\n📝 SQL QUERY:\n")
                click.echo(f"  {result.output['sql']}\n")

            if "explanation" in result.output:
                click.echo("💡 EXPLANATION:")
                click.echo(f"  {result.output['explanation']}\n")

            if verbose and "tables_needed" in result.output:
                click.echo("📊 ANALYSIS:")
                click.echo(f"  Tables: {result.output.get('tables_needed', [])}")
                click.echo(f"  Columns: {result.output.get('columns_needed', [])}")
                click.echo(f"  Operation: {result.output.get('operation_type', 'N/A')}")

        else:
            click.echo(f"\n❌ Generation failed: {result.error}", err=True)

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
    """Run with a sample question."""
    sample_schema = """
    CREATE TABLE users (
        id INT PRIMARY KEY,
        name VARCHAR(100),
        email VARCHAR(100),
        age INT,
        created_at TIMESTAMP
    );

    CREATE TABLE orders (
        id INT PRIMARY KEY,
        user_id INT REFERENCES users(id),
        product VARCHAR(100),
        amount DECIMAL(10,2),
        status VARCHAR(20),
        created_at TIMESTAMP
    );
    """

    sample_question = "Find all users who have placed orders over $100 in the last month"

    click.echo("Running demo...\n")
    click.echo(f"Question: {sample_question}\n")

    context = {"question": sample_question, "schema": sample_schema}
    result = asyncio.run(default_agent.run(context))

    if result.success:
        click.echo("=" * 50)
        click.echo("DEMO RESULT")
        click.echo("=" * 50)

        if "sql" in result.output:
            click.echo("\n📝 GENERATED SQL:\n")
            click.echo(f"  {result.output['sql']}\n")

        if "explanation" in result.output:
            click.echo(f"💡 {result.output['explanation']}\n")
    else:
        click.echo(f"❌ Demo failed: {result.error}")


if __name__ == "__main__":
    cli()
