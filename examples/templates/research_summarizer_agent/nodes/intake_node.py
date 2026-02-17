from framework.graph.node import NodeSpec

intake_node = NodeSpec(
    id="intake",
    name="Topic Intake",
    description="Ask user what topic they want researched",
    node_type="event_loop",
    client_facing=True,
    input_keys=[],
    output_keys=["research_topic"],
    system_prompt=(
        "Ask the user what topic they want researched and summarized. "
        "After user replies, call set_output('research_topic', topic)."
    ),
)
