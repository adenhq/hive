# Brand-Influencer Matchmaker Agent

> **Autonomous agent that analyzes brand-influencer alignment and generates match scores for partnership evaluation.**

This agent template addresses the challenge faced by Sales and Marketing teams in the creator economy who spend hours manually vetting influencers for brand partnerships. It provides an autonomous way to verify Brand-Influencer Alignment based on real-time data.

## 🎯 Problem Solved

For sales reps, manual influencer vetting is a massive bottleneck that slows down deal flow. This agent automates the process by:

1. Extracting **Brand DNA** (values, tone, target audience) from brand websites
2. Analyzing **Influencer Content** and public persona through search
3. Calculating a **Match Score** (0-100) based on qualitative alignment
4. Generating a **Sales Brief** with specific Pros and Red Flags

## 🏗️ Architecture

```
┌─────────────────┐     ┌─────────────────────┐     ┌─────────────────┐     ┌──────────────────┐
│  Brand Analyst  │ ──▶ │ Influencer Discovery│ ──▶ │ Reasoning Node  │ ──▶ │ Output Formatter │
│  (web_scrape)   │     │ (brave_web_search)  │     │ (llm_generate)  │     │ (llm_generate)   │
└─────────────────┘     └─────────────────────┘     └─────────────────┘     └──────────────────┘
       │                          │                         │                        │
       ▼                          ▼                         ▼                        ▼
  Brand Profile            Influencer Profile         Match Score (0-100)      Sales Brief
  • Values                 • Content Themes           • Alignment Breakdown    • Executive Summary
  • Tone                   • Audience Sentiment       • Pros                   • Recommendation
  • Target Audience        • Controversies            • Red Flags              • Next Steps
```

## ✨ Key Features

### Self-Healing Workflow
If the agent hits a paywall or restricted social media profile, it autonomously "self-heals" by pivoting to:
- News articles and interviews
- Secondary mentions and press coverage
- Podcast appearances or YouTube features

### Outcome-Driven Execution
Unlike simple linear chains, the agent won't stop until it has enough data to justify its score. It validates data quality and adjusts confidence levels accordingly.

### CRM-Ready Output
The Sales Brief is structured for easy integration with CRM systems, including:
- Recommendation levels (`strongly_recommend`, `recommend`, `proceed_with_caution`, `not_recommended`)
- Parseable JSON output
- Markdown export for reports

## 📊 Scoring Methodology

| Criterion | Weight | Description |
|-----------|--------|-------------|
| Values Alignment | 30 pts | Does the influencer's content align with brand values? |
| Audience Overlap | 25 pts | Does the audience match the brand's target demographic? |
| Tone Compatibility | 20 pts | Is communication style compatible? |
| Risk Assessment | 15 pts | Controversies, scandals, reputation risks |
| Authenticity | 10 pts | Genuine engagement vs. bot-like activity |

### Score Interpretation

| Score Range | Tier | Recommendation |
|-------------|------|----------------|
| 80-100 | Excellent Match | Strongly Recommend |
| 60-79 | Good Match | Recommend |
| 40-59 | Moderate Match | Proceed with Caution |
| 20-39 | Weak Match | Not Recommended |
| 0-19 | Poor Match | Strong Advise Against |

## 🚀 Usage

### From CLI

```bash
# Set up Python path
export PYTHONPATH=$PYTHONPATH:$(pwd)/core:$(pwd)/exports

# Run the matchmaker
python -m framework.cli run exports/brand_influencer_matchmaker --input '{
  "brand_url": "https://www.patagonia.com",
  "influencer_handle": "@sustainableamber"
}'
```

### Programmatic Usage

```python
from framework.runner import AgentRunner
import asyncio

async def analyze_match():
    runner = AgentRunner.from_file("exports/brand_influencer_matchmaker/agent.json")
    
    result = await runner.run({
        "brand_url": "https://www.nike.com",
        "influencer_handle": "MrBeast"
    })
    
    if result.success:
        sales_brief = result.output.get("sales_brief")
        print(f"Match Score: {result.output.get('match_score')}/100")
        print(f"Recommendation: {sales_brief.get('recommendation')}")
    else:
        print(f"Error: {result.error}")

asyncio.run(analyze_match())
```

## 📁 Files

| File | Description |
|------|-------------|
| `agent.json` | Agent definition with graph, goal, and nodes |
| `models.py` | Pydantic schemas for structured output |
| `README.md` | This documentation |
| `mcp_servers.json` | MCP server configuration for tools |

## 🔧 Required Tools

This agent requires the following MCP tools:
- `web_scrape` - For extracting content from brand websites
- `brave_web_search` - For searching influencer information

## 📈 Example Output

```json
{
  "match_score": 78,
  "match_tier": "Good Match",
  "recommendation": "recommend",
  "executive_summary": "Strong values alignment with Patagonia's sustainability focus. Influencer has authentic engagement and no major controversies. Audience overlap is moderate with room for growth.",
  "pros": [
    "Influencer regularly creates sustainability content",
    "Authentic engagement with genuine comments",
    "Previous successful brand partnerships in outdoor space"
  ],
  "red_flags": [
    "Audience skews younger than Patagonia's core demographic",
    "Limited experience with premium brand positioning"
  ],
  "next_steps": [
    "Schedule intro call with influencer's management",
    "Request audience demographics data",
    "Discuss potential content themes for collaboration"
  ]
}
```

## 🔗 References

- **Issue**: [#4127 - Agent Template: Autonomous Brand-Influencer Affinity & Match Scorer](https://github.com/adenhq/hive/issues/4127)
- **Author**: [@Samir-atra](https://github.com/Samir-atra)

## 📝 License

This agent template is part of the Hive Agent Framework and follows the same license terms.
