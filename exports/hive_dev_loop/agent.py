"""
================================================================================
HIVE DEV LOOP: ENTERPRISE AUTONOMOUS TDD AGENT
================================================================================
Description:
A fully autonomous Test-Driven Development (TDD) reference implementation.
This agent bypasses strict ToolRegistry limitations by implementing
"Tool Chaining" directly into the Graph architecture.
================================================================================
"""

import ast
import asyncio
import difflib
import logging
import os
import re
import shutil
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

import litellm

# ------------------------------------------------------------------------------
# HIVE FRAMEWORK IMPORTS
# ------------------------------------------------------------------------------
from framework.graph import EdgeCondition, EdgeSpec, Goal, GraphSpec, NodeSpec
from framework.graph.executor import GraphExecutor
from framework.runtime.core import Runtime

# ==============================================================================
# 1. ENTERPRISE CONFIGURATION (THE TOGGLE SWITCH)
# ==============================================================================

#  Set this to False before you push to GitHub!
USE_LOCAL_TESTING = False

if USE_LOCAL_TESTING:
    os.environ["LITELLM_MODEL"] = "ollama/qwen2.5-coder:1.5b"
else:
    os.environ["LITELLM_MODEL"] = "anthropic/claude-3-5-sonnet-20240620"

os.environ.setdefault("OLLAMA_API_BASE", "http://127.0.0.1:11434")

WORKSPACE_DIR = Path("./agent_workspace")
LOG_DIR = Path("./devloop_logs")
TEST_FILE = "solution_test.py"
CODE_FILE = "solution.py"


def setup_logger() -> logging.Logger:
    logger = logging.getLogger("Hive_Enterprise_Architect")
    logger.setLevel(logging.DEBUG)
    if not logger.handlers:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        os.makedirs(LOG_DIR, exist_ok=True)
        file_handler = logging.FileHandler(LOG_DIR / "agent_run.log", encoding="utf-8")
        formatter = logging.Formatter("[%(asctime)s] [%(levelname)-7s] => %(message)s")
        console_handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)
    return logger


logger = setup_logger()


# 2. ENTERPRISE UTILITIES (TELEMETRY, PARSERS, ANALYZERS)


class TelemetryTracker:
    def __init__(self):
        self.start_time = time.time()
        self.total_tokens = 0

    def add_tokens(self, count: int):
        self.total_tokens += count

    def get_metrics(self) -> Dict[str, Any]:
        return {
            "execution_time_seconds": round(time.time() - self.start_time, 2),
            "simulated_tokens_used": self.total_tokens,
        }


telemetry = TelemetryTracker()


class WorkspaceManager:
    @staticmethod
    def initialize():
        logger.info("[SYSTEM] Initializing clean workspace sandbox...")
        if WORKSPACE_DIR.exists():
            shutil.rmtree(WORKSPACE_DIR)
        WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
        (WORKSPACE_DIR / "__init__.py").touch()

    @staticmethod
    def extract_python_code(text: str) -> str:
        blocks = re.findall(r"```python\n(.*?)\n```", text, re.DOTALL)
        return (
            blocks[0]
            if blocks
            else text.replace("```python", "").replace("```", "").strip()
        )


class StaticAnalyzer:
    @staticmethod
    def is_valid_syntax(code: str, filename: str) -> bool:
        try:
            ast.parse(code)
            return True
        except SyntaxError as e:
            logger.error(f"[LINT] SyntaxError detected in {filename}: {e}")
            return False


class CodeDiffer:
    @staticmethod
    def generate_diff(old_code: str, new_code: str, filename: str) -> str:
        diff = difflib.unified_diff(
            old_code.splitlines(keepends=True),
            new_code.splitlines(keepends=True),
            fromfile=f"a/{filename}",
            tofile=f"b/{filename}",
            n=3,
        )
        return "".join(diff)


def ask_llm(system_prompt: str, user_prompt: str) -> str:
    model = os.getenv("LITELLM_MODEL", "ollama/qwen2.5-coder:1.5b")
    # Only use local API base if we are using Ollama, otherwise let LiteLLM handle Claude natively
    api_base = os.getenv("OLLAMA_API_BASE") if "ollama" in model else None

    logger.info(f"[LLM Engine] Prompting {model}...")
    try:
        response = litellm.completion(
            model=model,
            api_base=api_base,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        telemetry.add_tokens(100)
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"[LLM Error] {e}")
        return f"ERROR: {str(e)}"


# ==============================================================================
# 3. ROBUST GRAPH FUNCTIONS
# ==============================================================================


def plan_task(task: str) -> str:
    sys = "You are a Lead Architect. Write a brief execution plan for the user's task."
    plan = ask_llm(sys, f"Task: {task}")
    return f"TASK|{task}:::PLAN|{plan}"


def write_test(plan_payload: str) -> str:
    task = plan_payload.split(":::")[0].replace("TASK|", "")
    plan = plan_payload.split(":::")[1].replace("PLAN|", "")
    sys = "You are an SDET. Write a failing pytest suite. Wrap code in ```python ```"
    raw_test = ask_llm(sys, f"Task: {task}\nPlan:\n{plan}")
    return f"TASK|{task}:::TEST|{raw_test}"


def tool_save_test(test_payload: str) -> str:
    logger.info("--- [TOOL: FILES] SAVING TEST SUITE ---")
    task = test_payload.split(":::")[0].replace("TASK|", "")
    raw_test = test_payload.split(":::")[1].replace("TEST|", "")
    clean_code = WorkspaceManager.extract_python_code(raw_test)
    if StaticAnalyzer.is_valid_syntax(clean_code, TEST_FILE):
        (WORKSPACE_DIR / TEST_FILE).write_text(clean_code, encoding="utf-8")
    return f"TASK|{task}"


def write_code(save_test_status: str) -> str:
    task = save_test_status.replace("TASK|", "")
    sys = "You are a Python Developer. Write implementation code. Wrap code in ```python ```"
    raw_code = ask_llm(sys, f"Task: {task}")
    return f"TASK|{task}:::CODE|{raw_code}"


def tool_save_code(code_payload: str) -> str:
    logger.info("--- [TOOL: FILES] SAVING IMPLEMENTATION ---")
    task = code_payload.split(":::")[0].replace("TASK|", "")
    raw_code = code_payload.split(":::")[1].replace("CODE|", "")
    clean_code = WorkspaceManager.extract_python_code(raw_code)
    if StaticAnalyzer.is_valid_syntax(clean_code, CODE_FILE):
        (WORKSPACE_DIR / CODE_FILE).write_text(clean_code, encoding="utf-8")
    return f"TASK|{task}"


def tool_run_pytest(save_code_status: str) -> str:
    logger.info("--- [TOOL: BASH] EXECUTING PYTEST ---")
    task = save_code_status.replace("TASK|", "")
    try:
        result = subprocess.run(
            ["pytest", str(WORKSPACE_DIR / TEST_FILE), "-v", "--tb=short"],
            capture_output=True,
            text=True,
            cwd=str(WORKSPACE_DIR.absolute()),
        )
        output = result.stdout + "\n" + result.stderr
        status = "PASS" if result.returncode == 0 else "FAIL"

        if status == "PASS":
            logger.info("[BASH] Pytest PASSED.")
        else:
            logger.warning("[BASH] Pytest FAILED. Routing to debugger.")

        return f"TASK|{task}:::LOGS|STATUS: {status}\n{output}"
    except Exception as e:
        return f"TASK|{task}:::LOGS|STATUS: FAIL\nSystem Error: {str(e)}"


def evaluate_and_fix(logs_payload: str) -> str:
    task = logs_payload.split(":::")[0].replace("TASK|", "")
    logs = logs_payload.split(":::")[1].replace("LOGS|", "")
    sys = "You are a Debugger. If logs say 'PASS', output exactly 'PASS_BYPASS'. If 'FAIL', output fixed python code in ```python ```"
    return ask_llm(sys, f"Task: {task}\nLogs:\n{logs}")


def tool_save_fix(fix_payload: str) -> str:
    logger.info("--- [TOOL: FILES] SAVING BUG FIXES ---")
    if "PASS_BYPASS" in fix_payload:
        logger.info("[FILES] No bugs. Bypassing fix.")
        return "FIX_BYPASSED"

    clean_code = WorkspaceManager.extract_python_code(fix_payload)
    old_code = ""
    if (WORKSPACE_DIR / CODE_FILE).exists():
        old_code = (WORKSPACE_DIR / CODE_FILE).read_text(encoding="utf-8")
        diff = CodeDiffer.generate_diff(old_code, clean_code, CODE_FILE)
        logger.debug(f"[DIFF] Applying patch:\n{diff}")

    (WORKSPACE_DIR / CODE_FILE).write_text(clean_code, encoding="utf-8")
    return "FIX_SAVED"


def tool_verify_pytest(verify_payload: str) -> str:
    logger.info("--- [TOOL: BASH] VERIFYING FIXES ---")
    result = subprocess.run(
        ["pytest", str(WORKSPACE_DIR / TEST_FILE), "-v", "--tb=short"],
        capture_output=True,
        text=True,
        cwd=str(WORKSPACE_DIR.absolute()),
    )
    return result.stdout + "\n" + result.stderr


def tool_finalize(final_logs: str) -> str:
    logger.info("--- [NODE: ARTIFACT] GENERATING FINAL REPORT ---")
    impl_code = (
        (WORKSPACE_DIR / CODE_FILE).read_text(encoding="utf-8")
        if (WORKSPACE_DIR / CODE_FILE).exists()
        else ""
    )
    test_code = (
        (WORKSPACE_DIR / TEST_FILE).read_text(encoding="utf-8")
        if (WORKSPACE_DIR / TEST_FILE).exists()
        else ""
    )
    metrics = telemetry.get_metrics()

    report = f"""# Hive-Dev-Loop Execution Report
Date: {datetime.now().isoformat()}

## Execution Metrics
* Total Time: {metrics["execution_time_seconds"]}s
* LLM Invocations (Simulated Tokens): {metrics["simulated_tokens_used"]}

## Final Implementation
```python\n{impl_code}\n```

## Test Suite
```python\n{test_code}\n```
"""
    (WORKSPACE_DIR / "execution_report.md").write_text(report, encoding="utf-8")
    logger.info("[ARTIFACT] execution_report.md created.")
    return "TDD CYCLE COMPLETE."


# ==============================================================================
# 4. GRAPH COMPILATION & EXECUTION
# ==============================================================================


async def main():
    # ⚡ INTERACTIVE USER INPUT FOR THE AGENT
    print("\n" + "=" * 80)
    print("🐝 HIVE DEV LOOP: ENTERPRISE TDD AGENT")
    print("=" * 80)
    user_task = input(
        "\n[USER INPUT] Enter the coding task you want the agent to build:\n> "
    )

    if not user_task.strip():
        user_task = "Write a python function that adds two numbers. Return 0 if both are negative."
        print(f"\n[SYSTEM] No input provided. Defaulting to: {user_task}")

    print("\n")
    logger.info("[MAIN] Booting Hive Dev Loop Enterprise Architecture...")
    WorkspaceManager.initialize()

    goal = Goal(
        id="tdd-agent",
        name="TDD Coder",
        description="Executes a self-correcting TDD loop.",
        success_criteria=[
            {
                "id": "pass",
                "description": "Pytest passes",
                "metric": "custom",
                "target": "any",
            }
        ],
    )

    nodes = [
        NodeSpec(
            id="plan_task",
            name="Plan",
            description="Plans task",
            node_type="function",
            function="plan_task",
            input_keys=["task"],
            output_keys=["plan_payload"],
        ),
        NodeSpec(
            id="write_test",
            name="Write Test",
            description="Writes pytest",
            node_type="function",
            function="write_test",
            input_keys=["plan_payload"],
            output_keys=["test_payload"],
        ),
        NodeSpec(
            id="tool_save_test",
            name="Save Test",
            description="Saves test",
            node_type="function",
            function="tool_save_test",
            input_keys=["test_payload"],
            output_keys=["save_test_status"],
        ),
        NodeSpec(
            id="write_code",
            name="Write Code",
            description="Writes code",
            node_type="function",
            function="write_code",
            input_keys=["save_test_status"],
            output_keys=["code_payload"],
        ),
        NodeSpec(
            id="tool_save_code",
            name="Save Code",
            description="Saves code",
            node_type="function",
            function="tool_save_code",
            input_keys=["code_payload"],
            output_keys=["save_code_status"],
        ),
        NodeSpec(
            id="tool_run_pytest",
            name="Run Pytest",
            description="Runs test",
            node_type="function",
            function="tool_run_pytest",
            input_keys=["save_code_status"],
            output_keys=["logs_payload"],
        ),
        NodeSpec(
            id="evaluate_and_fix",
            name="Debugger",
            description="Fixes code",
            node_type="function",
            function="evaluate_and_fix",
            input_keys=["logs_payload"],
            output_keys=["fix_payload"],
        ),
        NodeSpec(
            id="tool_save_fix",
            name="Save Fix",
            description="Saves fix",
            node_type="function",
            function="tool_save_fix",
            input_keys=["fix_payload"],
            output_keys=["verify_payload"],
        ),
        NodeSpec(
            id="tool_verify_pytest",
            name="Verify Pytest",
            description="Verifies fix",
            node_type="function",
            function="tool_verify_pytest",
            input_keys=["verify_payload"],
            output_keys=["final_logs"],
        ),
        NodeSpec(
            id="tool_finalize",
            name="Artifact Gen",
            description="Builds report",
            node_type="function",
            function="tool_finalize",
            input_keys=["final_logs"],
            output_keys=["final_result"],
        ),
    ]

    edges = [
        EdgeSpec(
            id="e1",
            source="plan_task",
            target="write_test",
            condition=EdgeCondition.ON_SUCCESS,
        ),
        EdgeSpec(
            id="e2",
            source="write_test",
            target="tool_save_test",
            condition=EdgeCondition.ON_SUCCESS,
        ),
        EdgeSpec(
            id="e3",
            source="tool_save_test",
            target="write_code",
            condition=EdgeCondition.ON_SUCCESS,
        ),
        EdgeSpec(
            id="e4",
            source="write_code",
            target="tool_save_code",
            condition=EdgeCondition.ON_SUCCESS,
        ),
        EdgeSpec(
            id="e5",
            source="tool_save_code",
            target="tool_run_pytest",
            condition=EdgeCondition.ON_SUCCESS,
        ),
        EdgeSpec(
            id="e6",
            source="tool_run_pytest",
            target="evaluate_and_fix",
            condition=EdgeCondition.ON_SUCCESS,
        ),
        EdgeSpec(
            id="e7",
            source="evaluate_and_fix",
            target="tool_save_fix",
            condition=EdgeCondition.ON_SUCCESS,
        ),
        EdgeSpec(
            id="e8",
            source="tool_save_fix",
            target="tool_verify_pytest",
            condition=EdgeCondition.ON_SUCCESS,
        ),
        EdgeSpec(
            id="e9",
            source="tool_verify_pytest",
            target="tool_finalize",
            condition=EdgeCondition.ON_SUCCESS,
        ),
    ]

    graph = GraphSpec(
        id="hive-dev-loop-agent",
        goal_id="tdd-agent",
        entry_node="plan_task",
        terminal_nodes=["tool_finalize"],
        nodes=nodes,
        edges=edges,
    )

    executor = GraphExecutor(runtime=Runtime(storage_path=LOG_DIR))

    for func_name, func in [
        ("plan_task", plan_task),
        ("write_test", write_test),
        ("tool_save_test", tool_save_test),
        ("write_code", write_code),
        ("tool_save_code", tool_save_code),
        ("tool_run_pytest", tool_run_pytest),
        ("evaluate_and_fix", evaluate_and_fix),
        ("tool_save_fix", tool_save_fix),
        ("tool_verify_pytest", tool_verify_pytest),
        ("tool_finalize", tool_finalize),
    ]:
        executor.register_function(func_name, func)

    logger.info("[MAIN] Architecture locked. Injecting user payload...")

    result = await executor.execute(
        graph=graph, goal=goal, input_data={"task": user_task}
    )

    if result.success:
        logger.info("\n[RESULT] GRAPH EXECUTION STATUS: SUCCESS")
    else:
        logger.error(f"\n[CRITICAL] GRAPH EXECUTION FAILED: {result.error}")


if __name__ == "__main__":
    asyncio.run(main())
