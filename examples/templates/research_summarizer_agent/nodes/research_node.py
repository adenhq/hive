from framework.graph.node import NodeSpec

research_node = NodeSpec(
    id="research",
    name="Research Topic",
    description="Search web and gather info",
    node_type="event_loop",
    client_facing=False,
    input_keys=["research_topic"],
    output_keys=["research_data"],
    tools=["web_search", "web_scrape"],
    system_prompt=(
        "Search the web for information about research_topic. "
        "Use web_search and web_scrape. "
        "Extract key insights and structured notes. "
        "Call set_output('research_data', summary)."
    ),
)
