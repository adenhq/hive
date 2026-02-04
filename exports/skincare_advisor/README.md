# Skincare Product Advisor

Evaluate beauty and skincare products based on three pillars: ingredient safety, personalized skin compatibility, and aggregated user reviews. Maintains persistent memory of your skincare routine and product reactions.

## Features

- **Ingredient Analysis** — Looks up full ingredient lists and rates each for comedogenic potential (0-5 scale)
- **Skin Compatibility** — Predicts how your specific skin will react based on your profile, routine, and known sensitivities
- **Review Aggregation** — Searches multiple platforms (Sephora, Reddit, beauty blogs) for real user feedback
- **Three-Pillar Rating** — Weighted breakdown: Ingredients (35%), Compatibility (35%), Reviews (30%)
- **Persistent Memory** — Stores your skin profile, routine, and product reactions for future evaluations
- **Routine Tracking** — Add products to your routine and log how your skin reacts over time

## Workflow

```
load-user-profile → analyze-ingredients → aggregate-reviews → assess-skin-compatibility → synthesize-rating → update-memory
```

1. **Load User Profile** — Retrieves stored skin profile or collects new information
2. **Analyze Ingredients** — Researches product ingredients and comedogenic ratings
3. **Aggregate Reviews** — Searches for user reviews across multiple platforms
4. **Assess Skin Compatibility** — Predicts skin reaction based on profile + ingredients + routine
5. **Synthesize Rating** — Combines all three pillars into a final score and recommendation
6. **Update Memory** — Saves profile, evaluation history, and routine updates

## Usage

### CLI Commands

```bash
cd /Users/lilyadlin/hive

# Validate agent structure
PYTHONPATH=core:exports python -m skincare_advisor validate

# Show agent info
PYTHONPATH=core:exports python -m skincare_advisor info

# Evaluate a product
PYTHONPATH=core:exports python -m skincare_advisor run \
  --user-id "jane" \
  --product "CeraVe Moisturizing Cream" \
  --skin-type "dry"

# With existing routine context
PYTHONPATH=core:exports python -m skincare_advisor run \
  --user-id "jane" \
  --product "The Ordinary Niacinamide 10% + Zinc 1%" \
  --skin-type "oily" \
  --routine '["CeraVe Foaming Cleanser", "Paula Choice BHA", "CeraVe PM Moisturizer"]'

# Update routine with reaction feedback
PYTHONPATH=core:exports python -m skincare_advisor run \
  --user-id "jane" \
  --product "The Ordinary Niacinamide 10% + Zinc 1%" \
  --update "Added to routine 2 weeks ago. Skin feels smoother, no breakouts."

# Interactive session
PYTHONPATH=core:exports python -m skincare_advisor shell

# Mock mode (no API calls)
PYTHONPATH=core:exports python -m skincare_advisor run \
  --user-id "test" \
  --product "Test Product" \
  --mock
```

### Python API

```python
import asyncio
from skincare_advisor import SkincareAdvisorAgent

agent = SkincareAdvisorAgent()

result = asyncio.run(agent.run({
    "user_id": "jane",
    "product_query": "Evaluate: CeraVe Moisturizing Cream. Skin type: dry.",
    "routine_update": "",
}))

if result.success:
    print(f"Rating: {result.output['overall_rating']}/10")
    print(f"Recommendation: {result.output['recommendation']}")
    print(result.output['detailed_report'])
```

## Rating Scale

| Score | Recommendation | Meaning |
|-------|---------------|---------|
| 9-10 | Strongly Recommend | Excellent match for your skin |
| 7-8.9 | Recommend | Good product with minor caveats |
| 5-6.9 | Neutral | Mixed results, proceed with caution |
| 3-4.9 | Caution | Significant concerns identified |
| 0-2.9 | Avoid | Poor match for your skin |

## Data Storage

User profiles are stored locally at `./skincare_profiles/{user_id}.json` and include:
- Skin profile (type, sensitivities, concerns)
- Current routine
- Product evaluation history
- Reaction log for added products
