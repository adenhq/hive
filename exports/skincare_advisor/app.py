"""
Skincare Product Advisor — Streamlit Chatbot Interface
"""

import json
from datetime import date
from pathlib import Path

import anthropic
import streamlit as st

# ── Page config ──────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Skincare Advisor",
    page_icon="🧴",
    layout="centered",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ───────────────────────────────────────────────────────────
st.markdown(
    """
<style>
    /* overall background & font */
    .stApp {
        background: linear-gradient(135deg, #fdf6f0 0%, #f5e6f0 50%, #e8f4f8 100%);
    }

    /* header area */
    .header-container {
        text-align: center;
        padding: 1.2rem 0 0.6rem 0;
    }
    .header-container h1 {
        font-family: 'Georgia', serif;
        color: #6b4c6e;
        font-size: 2rem;
        margin-bottom: 0.2rem;
    }
    .header-container p {
        color: #9b8a9e;
        font-size: 0.95rem;
    }

    /* chat bubbles */
    .stChatMessage {
        border-radius: 16px !important;
        margin-bottom: 0.7rem !important;
    }

    /* rating card */
    .rating-card {
        background: white;
        border-radius: 16px;
        padding: 1.5rem;
        box-shadow: 0 2px 12px rgba(107, 76, 110, 0.08);
        margin: 0.8rem 0;
    }
    .rating-header {
        font-size: 1.3rem;
        font-weight: 700;
        color: #6b4c6e;
        margin-bottom: 0.3rem;
    }
    .rating-score {
        font-size: 2.4rem;
        font-weight: 800;
        background: linear-gradient(135deg, #c084a0, #8b6bb0);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .pillar-row {
        display: flex;
        gap: 0.8rem;
        margin-top: 1rem;
    }
    .pillar-box {
        flex: 1;
        background: #faf5fc;
        border-radius: 12px;
        padding: 1rem;
        text-align: center;
    }
    .pillar-box .score {
        font-size: 1.4rem;
        font-weight: 700;
        color: #6b4c6e;
    }
    .pillar-box .label {
        font-size: 0.75rem;
        color: #9b8a9e;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-top: 0.2rem;
    }

    /* sidebar styling */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #f8f0f8 0%, #fff 100%);
    }
    [data-testid="stSidebar"] h2 {
        color: #6b4c6e;
    }

    /* profile pill tags */
    .profile-tag {
        display: inline-block;
        background: #f0e6f6;
        color: #6b4c6e;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.8rem;
        margin: 0.15rem;
    }
</style>
""",
    unsafe_allow_html=True,
)

# ── State defaults ───────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []
if "profile" not in st.session_state:
    st.session_state.profile = {}
if "evaluation_history" not in st.session_state:
    st.session_state.evaluation_history = []

# ── System prompt (encapsulates the agent's full logic) ──────────────────
SYSTEM_PROMPT = """\
You are a Skincare Product Advisor chatbot. You help users evaluate skincare and beauty products based on three pillars.

## Your Capabilities
You evaluate products using THREE PILLARS, each with a score from 0-10:

### Pillar 1 — Ingredient Safety (35% weight)
- Analyze every ingredient for comedogenic potential (0-5 scale)
- Flag irritants, allergens, and sensitizers
- Reference databases like INCIDecoder, CosDNA, EWG Skin Deep
- Rate overall ingredient safety from 0-10

### Pillar 2 — Skin Compatibility (35% weight)
- Assess the product against the user's specific skin type
- Cross-reference with known sensitivities
- Check for interactions with their current routine products (e.g. retinol + AHA, vitamin C + niacinamide)
- Rate personalized compatibility from 0-10

### Pillar 3 — User Reviews (30% weight)
- Summarize what real users say about this product
- Note common praises and complaints
- Highlight skin-type-specific feedback
- Rate review sentiment from 0-10

## Rating Scale
- 9-10: ✨ Strongly Recommend — Excellent match
- 7-8.9: 👍 Recommend — Good with minor caveats
- 5-6.9: ⚖️ Neutral — Mixed, proceed with caution
- 3-4.9: ⚠️ Caution — Significant concerns
- 0-2.9: 🚫 Avoid — Poor match

## How to Respond

When the user asks about a product:
1. First acknowledge their question
2. Provide a structured rating with all three pillars
3. Give a clear recommendation
4. Mention any interaction warnings with their current routine

ALWAYS structure your product evaluation response with this exact format for the rating summary:

**Overall Rating: X.X/10 — [Recommendation]**

| Pillar | Score | Key Finding |
|--------|-------|-------------|
| 🧪 Ingredients | X.X/10 | [one-line summary] |
| 🧬 Skin Compatibility | X.X/10 | [one-line summary] |
| ⭐ User Reviews | X.X/10 | [one-line summary] |

Then provide the detailed breakdown for each pillar.

## Important Rules
- NEVER provide medical diagnoses. Always suggest seeing a dermatologist for persistent issues.
- Be evidence-based — cite ingredient databases and known comedogenic ratings.
- Be transparent about your scoring methodology.
- If you don't have enough info about the user's skin, ASK before evaluating.
- When the user wants to add a product to their routine, confirm and note it.
- When the user reports a reaction, log it and update your understanding of their skin.

## User Profile
{profile_context}

## Conversation Style
Be warm, knowledgeable, and concise. Use a friendly but professional tone — like a well-informed friend who happens to know a lot about skincare science. Keep responses focused and scannable.
"""

PROFILES_DIR = Path("./skincare_profiles")


def _load_profile(user_id: str) -> dict:
    """Load profile from local JSON file."""
    path = PROFILES_DIR / f"{user_id}.json"
    if path.exists():
        return json.loads(path.read_text())
    return {}


def _save_profile(user_id: str, profile: dict):
    """Save profile to local JSON file."""
    PROFILES_DIR.mkdir(parents=True, exist_ok=True)
    path = PROFILES_DIR / f"{user_id}.json"
    profile["last_updated"] = str(date.today())
    path.write_text(json.dumps(profile, indent=2))


def _build_profile_context() -> str:
    """Build the profile context string for the system prompt."""
    p = st.session_state.profile
    if not p:
        return "No profile set yet. Ask the user about their skin type and routine before evaluating."

    parts = [f"Name: {p.get('name', 'Unknown')}"]
    if p.get("skin_type"):
        parts.append(f"Skin type: {p['skin_type']}")
    if p.get("concerns"):
        parts.append(f"Concerns: {', '.join(p['concerns'])}")
    if p.get("sensitivities"):
        parts.append(f"Sensitivities/Allergens: {', '.join(p['sensitivities'])}")
    if p.get("routine"):
        parts.append(f"Current routine: {', '.join(p['routine'])}")
    if st.session_state.evaluation_history:
        recent = st.session_state.evaluation_history[-5:]
        history_lines = [f"  - {e['product']}: {e['rating']}/10 ({e['rec']})" for e in recent]
        parts.append("Recent evaluations:\n" + "\n".join(history_lines))
    return "\n".join(parts)


# ── Sidebar: Profile Setup ───────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🪞 Your Skin Profile")

    api_key = st.text_input(
        "Anthropic API Key",
        type="password",
        help="Required to power the advisor. Get one at console.anthropic.com",
    )

    st.divider()

    name = st.text_input("Your name", value=st.session_state.profile.get("name", ""))

    skin_type = st.selectbox(
        "Skin type",
        ["", "Normal", "Oily", "Dry", "Combination", "Sensitive"],
        index=0,
        help="Select your primary skin type",
    )

    concerns = st.multiselect(
        "Skin concerns",
        ["Acne", "Aging", "Hyperpigmentation", "Redness", "Dryness", "Oiliness", "Large pores", "Dark circles", "Texture"],
        default=st.session_state.profile.get("concerns", []),
    )

    sensitivities = st.text_input(
        "Known sensitivities",
        value=", ".join(st.session_state.profile.get("sensitivities", [])),
        help="Ingredients you react to, comma-separated (e.g. fragrance, retinol)",
    )

    routine = st.text_area(
        "Current routine products",
        value="\n".join(st.session_state.profile.get("routine", [])),
        help="One product per line",
        height=100,
    )

    if st.button("💾  Save Profile", use_container_width=True):
        profile = {
            "name": name,
            "skin_type": skin_type,
            "concerns": concerns,
            "sensitivities": [s.strip() for s in sensitivities.split(",") if s.strip()],
            "routine": [r.strip() for r in routine.strip().split("\n") if r.strip()],
        }
        st.session_state.profile = profile
        if name:
            _save_profile(name.lower().replace(" ", "_"), profile)
        st.success("Profile saved!")

    # show current profile summary
    if st.session_state.profile.get("skin_type"):
        st.divider()
        st.markdown("### Active Profile")
        p = st.session_state.profile
        tags_html = f'<span class="profile-tag">{p["skin_type"]} skin</span>'
        for c in p.get("concerns", []):
            tags_html += f'<span class="profile-tag">{c}</span>'
        st.markdown(tags_html, unsafe_allow_html=True)

    st.divider()
    st.caption("Your data is stored locally only — never sent to third parties.")

# ── Header ───────────────────────────────────────────────────────────────
st.markdown(
    """
<div class="header-container">
    <h1>🧴 Skincare Advisor</h1>
    <p>Ask me about any skincare or beauty product — I'll rate it for your skin.</p>
</div>
""",
    unsafe_allow_html=True,
)

# ── Chat history ─────────────────────────────────────────────────────────
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ── Chat input ───────────────────────────────────────────────────────────
if prompt := st.chat_input("Ask about a product... e.g. 'Rate CeraVe Moisturizing Cream'"):
    # guard: need API key
    if not api_key:
        st.error("Please enter your Anthropic API key in the sidebar to get started.")
        st.stop()

    # add user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # build system prompt with current profile
    system = SYSTEM_PROMPT.format(profile_context=_build_profile_context())

    # prepare messages for API
    api_messages = [
        {"role": m["role"], "content": m["content"]}
        for m in st.session_state.messages
    ]

    # call Anthropic API
    with st.chat_message("assistant"):
        with st.spinner("Analyzing..."):
            try:
                client = anthropic.Anthropic(api_key=api_key)
                response = client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=4096,
                    system=system,
                    messages=api_messages,
                )
                reply = response.content[0].text
            except anthropic.AuthenticationError:
                reply = "Invalid API key. Please check the key in the sidebar and try again."
            except Exception as e:
                reply = f"Something went wrong: {e}"

        st.markdown(reply)

    st.session_state.messages.append({"role": "assistant", "content": reply})
