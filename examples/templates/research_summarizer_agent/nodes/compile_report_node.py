from framework.graph.node import NodeSpec

compile_report_node = NodeSpec(
    id="compile-report",
    name="Compile Summary",
    description="Create final structured summary",
    node_type="event_loop",
    client_facing=False,
    input_keys=["research_data"],
    output_keys=["final_report"],
    tools=["save_data", "serve_file_to_user"],
    system_prompt=(
        "Create a structured summary from research_data. "
        "Use bullet points and sections. "
        "Save using save_data and provide to user using serve_file_to_user. "
        "Then call set_output('final_report','done')."
    ),
)
