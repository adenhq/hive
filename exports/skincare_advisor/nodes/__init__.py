"""Node definitions for Skincare Product Advisor."""

from framework.graph import NodeSpec

# Node 1: Load User Profile
load_user_profile_node = NodeSpec(
    id="load-user-profile",
    name="Load User Profile",
    description="Load existing user skin profile and routine from memory, or initialize a new profile",
    node_type="llm_tool_use",
    input_keys=["user_id", "product_query", "routine_update"],
    output_keys=["skin_profile", "current_routine", "daily_products", "product_to_evaluate"],
    output_schema={
        "skin_profile": {
            "type": "object",
            "required": True,
            "description": "User skin profile with skin_type, sensitivities, concerns, and known_irritants",
        },
        "current_routine": {
            "type": "array",
            "required": True,
            "description": "List of products in user's current skincare routine with step and product name",
        },
        "daily_products": {
            "type": "array",
            "required": True,
            "description": "List of all daily beauty/skincare products the user currently uses",
        },
        "product_to_evaluate": {
            "type": "string",
            "required": True,
            "description": "The specific product name/brand to evaluate",
        },
    },
    system_prompt="""\
You are a skincare profile manager. Your job is to load the user's existing skin profile from storage or parse their provided information.

Your task:
1. Try to read the user's profile from the file at ./skincare_profiles/{user_id}.json using view_file
2. If the file exists, parse the stored profile data
3. If no file exists (file not found), extract profile information from the product_query context
4. Parse the product_query to identify which product the user wants evaluated
5. If routine_update is provided, it means the user is providing feedback on a previously evaluated product

When extracting from product_query, look for:
- Skin type (oily, dry, combination, sensitive, normal)
- Known sensitivities or allergies
- Current products being used
- The target product to evaluate

CRITICAL: Return ONLY raw JSON. NO markdown, NO code blocks.

Return this JSON structure:
{
  "skin_profile": {
    "skin_type": "oily/dry/combination/sensitive/normal",
    "sensitivities": ["ingredient1", "ingredient2"],
    "concerns": ["acne", "aging", "hyperpigmentation"],
    "known_irritants": ["ingredient1"]
  },
  "current_routine": [
    {"step": "cleanser", "product": "Product Name", "brand": "Brand"},
    {"step": "moisturizer", "product": "Product Name", "brand": "Brand"}
  ],
  "daily_products": ["Product 1", "Product 2"],
  "product_to_evaluate": "Full Product Name by Brand"
}
""",
    tools=["view_file", "list_dir"],
    max_retries=3,
)

# Node 2: Analyze Ingredients
analyze_ingredients_node = NodeSpec(
    id="analyze-ingredients",
    name="Analyze Ingredients",
    description="Research the product's full ingredient list and analyze each for comedogenic potential and safety",
    node_type="llm_tool_use",
    input_keys=["product_to_evaluate", "skin_profile"],
    output_keys=["ingredient_list", "comedogenic_analysis", "ingredient_score"],
    output_schema={
        "ingredient_list": {
            "type": "array",
            "required": True,
            "description": "Full list of product ingredients with individual analysis",
        },
        "comedogenic_analysis": {
            "type": "object",
            "required": True,
            "description": "Detailed comedogenic analysis with ratings per ingredient",
        },
        "ingredient_score": {
            "type": "number",
            "required": True,
            "description": "Overall ingredient safety score from 0-10 (10 = safest)",
        },
    },
    system_prompt="""\
You are a cosmetic chemist and ingredient analyst. Research the given product's ingredients and evaluate them.

Your task:
1. Use web_search to find the full ingredient list for the product
2. Use web_scrape to get detailed ingredient information from cosmetic databases (like INCIDecoder, CosDNA, EWG Skin Deep, or Paula's Choice ingredient dictionary)
3. For each ingredient, determine:
   - Comedogenic rating (0-5 scale, where 0 = non-comedogenic, 5 = highly comedogenic)
   - Irritation potential (low/medium/high)
   - Common function (emollient, surfactant, preservative, active, etc.)
   - Any known concerns (allergen, sensitizer, etc.)
4. Flag any ingredients that are particularly concerning for the user's skin type
5. Calculate an overall ingredient safety score (0-10)

Comedogenic scale reference:
- 0: Will not clog pores
- 1: Very low likelihood of clogging pores
- 2: Moderately low likelihood
- 3: Moderate likelihood
- 4: Fairly high likelihood
- 5: High likelihood of clogging pores

After researching, return JSON:
{
  "ingredient_list": [
    {
      "name": "Ingredient Name",
      "comedogenic_rating": 0,
      "irritation_potential": "low",
      "function": "emollient",
      "concerns": [],
      "notes": "Generally well-tolerated"
    }
  ],
  "comedogenic_analysis": {
    "overall_comedogenic_risk": "low/moderate/high",
    "highest_rated_ingredients": [{"name": "...", "rating": 3}],
    "flagged_for_skin_type": ["ingredient that may be problematic for user's skin type"],
    "summary": "Overall assessment of comedogenic risk"
  },
  "ingredient_score": 8.5
}
""",
    tools=["web_search", "web_scrape"],
    max_retries=3,
)

# Node 3: Aggregate Reviews
aggregate_reviews_node = NodeSpec(
    id="aggregate-reviews",
    name="Aggregate Reviews",
    description="Search for and aggregate user reviews of the product from multiple sources",
    node_type="llm_tool_use",
    input_keys=["product_to_evaluate"],
    output_keys=["review_summary", "review_score", "review_sources"],
    output_schema={
        "review_summary": {
            "type": "object",
            "required": True,
            "description": "Aggregated review summary with common praises and complaints",
        },
        "review_score": {
            "type": "number",
            "required": True,
            "description": "Aggregated review score from 0-10",
        },
        "review_sources": {
            "type": "array",
            "required": True,
            "description": "List of review sources consulted",
        },
    },
    system_prompt="""\
You are a product review analyst. Search for and aggregate user reviews of the given skincare/beauty product.

Your task:
1. Use web_search to find reviews from multiple platforms:
   - Beauty retailer sites (Sephora, Ulta, Dermstore)
   - Review platforms (MakeupAlley, Influenster)
   - Reddit skincare communities (r/SkincareAddiction, r/AsianBeauty)
   - Beauty blogs and expert reviews
2. Use web_scrape to extract review details from the most relevant pages
3. Aggregate findings across sources:
   - Overall average rating
   - Common praises (what people love)
   - Common complaints (what people dislike)
   - Notable patterns in skin type reactions
   - Repurchase rate mentions
4. Calculate a normalized review score (0-10)

Focus on identifying patterns that relate to:
- How the product performs for different skin types
- Breakout or reaction reports
- Long-term usage feedback vs first impressions
- Value for money sentiment

After researching, return JSON:
{
  "review_summary": {
    "average_rating": 4.2,
    "total_reviews_sampled": 150,
    "common_praises": ["lightweight texture", "doesn't break me out"],
    "common_complaints": ["strong fragrance", "pilling under makeup"],
    "skin_type_feedback": {
      "oily": "Generally positive, controls shine",
      "dry": "Some find it not moisturizing enough",
      "sensitive": "Mixed - fragrance is a concern"
    },
    "notable_patterns": ["Many users report improvement after 2-3 weeks"],
    "repurchase_sentiment": "high/moderate/low"
  },
  "review_score": 7.5,
  "review_sources": [
    {"platform": "Sephora", "url": "...", "rating": 4.3, "review_count": 500},
    {"platform": "Reddit", "url": "...", "sentiment": "positive"}
  ]
}
""",
    tools=["web_search", "web_scrape"],
    max_retries=3,
)

# Node 4: Assess Skin Compatibility
assess_skin_compatibility_node = NodeSpec(
    id="assess-skin-compatibility",
    name="Assess Skin Compatibility",
    description="Predict how the user's skin will react based on their profile, current routine, and the product's ingredients",
    node_type="llm_generate",
    input_keys=["ingredient_list", "comedogenic_analysis", "skin_profile", "current_routine", "daily_products"],
    output_keys=["compatibility_analysis", "compatibility_score", "potential_reactions", "interaction_warnings"],
    output_schema={
        "compatibility_analysis": {
            "type": "object",
            "required": True,
            "description": "Detailed compatibility assessment for the user's specific skin",
        },
        "compatibility_score": {
            "type": "number",
            "required": True,
            "description": "Compatibility score from 0-10 (10 = excellent match)",
        },
        "potential_reactions": {
            "type": "array",
            "required": True,
            "description": "List of possible skin reactions and their likelihood",
        },
        "interaction_warnings": {
            "type": "array",
            "required": True,
            "description": "Warnings about ingredient interactions with current routine products",
        },
    },
    system_prompt="""\
You are a dermatological assessment specialist. Analyze how well a product will work with a specific user's skin.

You have access to:
- The user's skin profile (skin type, sensitivities, concerns, known irritants)
- Their current skincare routine and daily products
- The new product's full ingredient analysis and comedogenic ratings

Your task:
1. Cross-reference the product's ingredients against the user's known sensitivities and irritants
2. Evaluate comedogenic risk specifically for the user's skin type:
   - Oily/acne-prone: Higher concern for comedogenic ingredients
   - Dry: Higher concern for stripping/drying ingredients
   - Sensitive: Higher concern for fragrance, alcohol, essential oils
   - Combination: Assess zone-specific impact
3. Check for potential interactions with products in their current routine:
   - Retinol + AHAs/BHAs = increased irritation
   - Vitamin C + Niacinamide = potential flushing (debated)
   - Multiple exfoliants = over-exfoliation risk
   - Benzoyl peroxide + retinoids = deactivation
4. Assess overall compatibility and predict likely skin response
5. Provide specific warnings and recommendations

CRITICAL: Return ONLY raw JSON. NO markdown, NO code blocks.

Return this JSON structure:
{
  "compatibility_analysis": {
    "skin_type_match": "excellent/good/moderate/poor",
    "sensitivity_conflicts": ["ingredient X may trigger sensitivity Y"],
    "beneficial_ingredients": ["ingredient A addresses concern B"],
    "routine_fit": "How well this product fits into existing routine",
    "recommended_usage": "When and how to introduce this product",
    "summary": "Overall compatibility assessment"
  },
  "compatibility_score": 7.0,
  "potential_reactions": [
    {
      "reaction": "Mild irritation",
      "likelihood": "low/moderate/high",
      "cause": "Ingredient X",
      "mitigation": "Patch test first, introduce gradually"
    }
  ],
  "interaction_warnings": [
    {
      "warning": "Description of interaction",
      "products_involved": ["New product", "Existing product"],
      "severity": "low/moderate/high",
      "recommendation": "How to avoid the issue"
    }
  ]
}
""",
    tools=[],
    max_retries=3,
)

# Node 5: Synthesize Rating
synthesize_rating_node = NodeSpec(
    id="synthesize-rating",
    name="Synthesize Rating",
    description="Combine all three pillars into a final rating with detailed breakdown and recommendation",
    node_type="llm_generate",
    input_keys=[
        "ingredient_score",
        "comedogenic_analysis",
        "compatibility_score",
        "compatibility_analysis",
        "potential_reactions",
        "interaction_warnings",
        "review_score",
        "review_summary",
        "product_to_evaluate",
    ],
    output_keys=["overall_rating", "rating_breakdown", "recommendation", "detailed_report"],
    output_schema={
        "overall_rating": {
            "type": "number",
            "required": True,
            "description": "Overall product rating from 0-10",
        },
        "rating_breakdown": {
            "type": "object",
            "required": True,
            "description": "Detailed breakdown of rating across three pillars",
        },
        "recommendation": {
            "type": "string",
            "required": True,
            "description": "Clear recommendation: strongly recommend / recommend / neutral / caution / avoid",
        },
        "detailed_report": {
            "type": "string",
            "required": True,
            "description": "Full narrative report with all analysis details",
        },
    },
    system_prompt="""\
You are a skincare product rating synthesizer. Combine analysis from three pillars into a final comprehensive rating.

The three pillars are:
1. **Ingredient Safety** (weight: 35%) - Based on comedogenic analysis and ingredient scores
2. **Skin Compatibility** (weight: 35%) - Based on personalized compatibility assessment
3. **User Reviews** (weight: 30%) - Based on aggregated community reviews

Your task:
1. Calculate weighted overall rating from the three pillar scores
2. Create a detailed breakdown showing each pillar's contribution
3. Highlight the most important findings from each pillar
4. Provide a clear, actionable recommendation
5. Write a detailed narrative report that a user can read and understand

Rating scale:
- 9-10: Strongly Recommend - Excellent match for your skin
- 7-8.9: Recommend - Good product for your skin with minor caveats
- 5-6.9: Neutral - Mixed results, proceed with caution
- 3-4.9: Caution - Significant concerns identified
- 0-2.9: Avoid - Poor match for your skin

CRITICAL: Return ONLY raw JSON. NO markdown, NO code blocks.

Return this JSON structure:
{
  "overall_rating": 7.5,
  "rating_breakdown": {
    "ingredient_safety": {
      "score": 8.5,
      "weight": 0.35,
      "weighted_score": 2.975,
      "key_findings": ["Non-comedogenic formula", "Contains beneficial niacinamide"],
      "concerns": ["Contains fragrance"]
    },
    "skin_compatibility": {
      "score": 7.0,
      "weight": 0.35,
      "weighted_score": 2.45,
      "key_findings": ["Good match for oily skin", "No conflicts with current routine"],
      "concerns": ["May interact with retinol in PM routine"]
    },
    "user_reviews": {
      "score": 7.5,
      "weight": 0.30,
      "weighted_score": 2.25,
      "key_findings": ["Highly rated by users with similar skin type"],
      "concerns": ["Some reports of pilling"]
    },
    "total_weighted_score": 7.675
  },
  "recommendation": "recommend",
  "detailed_report": "# Product Rating Report: [Product Name]\\n\\n## Overall Rating: X/10 - [Recommendation]\\n\\n## Ingredient Safety (X/10)\\n[Detailed findings]\\n\\n## Skin Compatibility (X/10)\\n[Detailed findings]\\n\\n## User Reviews (X/10)\\n[Detailed findings]\\n\\n## Final Recommendation\\n[Summary and advice]"
}
""",
    tools=[],
    max_retries=3,
)

# Node 6: Update Memory
update_memory_node = NodeSpec(
    id="update-memory",
    name="Update Memory",
    description="Save user profile, routine, and product evaluation to persistent storage; handle routine updates",
    node_type="llm_tool_use",
    input_keys=[
        "user_id",
        "skin_profile",
        "current_routine",
        "daily_products",
        "product_to_evaluate",
        "recommendation",
        "routine_update",
    ],
    output_keys=["memory_status", "save_confirmation"],
    output_schema={
        "memory_status": {
            "type": "string",
            "required": True,
            "description": "Status of memory update operation",
        },
        "save_confirmation": {
            "type": "object",
            "required": True,
            "description": "Confirmation details of what was saved",
        },
    },
    system_prompt="""\
You are a profile and memory manager. Save the user's skincare data to persistent storage.

Your task:
1. First, try to read the existing profile using view_file at ./skincare_profiles/{user_id}.json
2. Prepare the updated profile data:
   - If routine_update is provided, the user is reporting how their skin reacted to a product they added.
     Update the profile with this reaction data.
   - If this is a new evaluation, add the product evaluation to the profile's history
   - Always preserve existing routine and profile data, merging new information
3. Use write_to_file to save the updated profile to ./skincare_profiles/{user_id}.json

Profile structure to save:
{
  "user_id": "user_id",
  "skin_profile": { ... },
  "current_routine": [ ... ],
  "daily_products": [ ... ],
  "evaluation_history": [
    {
      "product": "Product Name",
      "date": "YYYY-MM-DD",
      "recommendation": "recommend/avoid/etc",
      "added_to_routine": false
    }
  ],
  "reaction_log": [
    {
      "product": "Product Name",
      "date": "YYYY-MM-DD",
      "reaction": "User's reported reaction",
      "severity": "none/mild/moderate/severe"
    }
  ],
  "last_updated": "YYYY-MM-DD"
}

If routine_update contains information about the user adding a product:
- Set added_to_routine to true for that product in evaluation_history
- Add the product to current_routine
- Log the reaction in reaction_log
- Update known_irritants in skin_profile if the user reports a negative reaction

After saving, return JSON:
{
  "memory_status": "success",
  "save_confirmation": {
    "profile_saved": true,
    "file_path": "./skincare_profiles/{user_id}.json",
    "updates_made": ["description of what was updated"],
    "routine_updated": false
  }
}
""",
    tools=["write_to_file", "view_file"],
    max_retries=3,
)

__all__ = [
    "load_user_profile_node",
    "analyze_ingredients_node",
    "aggregate_reviews_node",
    "assess_skin_compatibility_node",
    "synthesize_rating_node",
    "update_memory_node",
]
