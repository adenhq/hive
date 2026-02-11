
# GTM Marketing Agent

A specialized agent that analyzes competitor messaging and drafts strategic marketing content to counter them.

## Overview

This agent helps marketing teams by automating the initial research and drafting phase of a campaign. It:
1.  **Analyzes** a competitor's website or product.
2.  **Identifies** their value proposition, target audience, and messaging gaps.
3.  **Drafts** 3 unique marketing assets (LinkedIn post, Ad copy, Email subjects) that position your product against theirs.

## Workflow

1.  **Intake**: Asks the user for a competitor URL or product name.
2.  **Competitor Analysis**: Scrapes the competitor's site to understand their positioning.
3.  **Draft Content**: Generates high-quality marketing copy based on the analysis.

## Usage

```bash
# Run with default settings
python -m examples.templates.marketing_agent

# Run with a specific model
python -m examples.templates.marketing_agent --model gpt-4o
```

## Configuration

You can configure the model and other settings in `config.py`.

## Requirements

-   `OPENAI_API_KEY` (or other LLM provider key) set in your environment.
