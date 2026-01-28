"""
Self-Healing Agent Framework.

Extends the standard runner to automatically detect implementation errors
and fix them by modifying source code during execution.
"""

import logging
import inspect
import textwrap
import traceback
from typing import Any, Callable
from pathlib import Path

from framework.graph.node import NodeProtocol, NodeContext, NodeResult, NodeSpec
from framework.graph.executor import GraphExecutor
from framework.runner.runner import AgentRunner

logger = logging.getLogger(__name__)

class SelfHealingNodeWrapper(NodeProtocol):
    """
    Wraps a node to intercept failures and trigger self-healing.
    """
    def __init__(
        self, 
        inner_node: NodeProtocol, 
        executor: "SelfHealingExecutor",
        node_spec: NodeSpec
    ):
        self.inner = inner_node
        self.executor = executor
        self.node_spec = node_spec

    async def execute(self, ctx: NodeContext) -> NodeResult:
        # First attempt
        result = await self.inner.execute(ctx)
        
        if result.success:
            return result
            
        # Check if we should attempt to heal
        # We heal if:
        # 1. Self-healing is enabled
        # 2. The error looks like a code/implementation error (vs a logical one)
        # 3. We haven't exceeded healing max retries
        
        if not self.executor.evolve_on_failure:
            return result

        # Heuristic: Is this a crash/exception or just a logical failure?
        # Typically crashes come with tracebacks or specific python exceptions in the error string.
        error_msg = result.error or ""
        is_crash = any(x in error_msg for x in [
            "Error:", "Exception:", "Traceback", "AttributeError", "TypeError", 
            "ValueError", "KeyError", "IndexError", "ImportError"
        ])
        
        if not is_crash:
            # Just a logic failure (e.g. LLM couldn't answer), normal retry logic applies
            return result
            
        logger.info(f"🚑 Detected crash in node '{self.node_spec.id}': {error_msg}")
        logger.info("   Initiating healing cycle...")
        
        # Determine which file defines this node
        try:
            # Unwrap exceptions to find the real implementation class
            impl_class = self.inner.__class__
            source_file = inspect.getsourcefile(impl_class)
            
            if not source_file:
                logger.warning("   ⚠ Could not locate source file for healing")
                return result
                
            # Perform healing
            healed = await self.executor.heal_node(
                error=error_msg,
                node_spec=self.node_spec,
                source_file=source_file,
                context=ctx
            )
            
            if healed:
                logger.info("   ✓ Healing successful. Retrying execution with patched code...")
                # Reload the node implementation
                # Note: Python's reload is tricky. For now, we assume the executor 
                # can re-instantiate or we might need to rely on process restart strategies later.
                # Ideally, we re-create the inner node.
                
                # Re-fetch implementation (this should pick up the new code if hot-reloaded appropriately 
                # or if we are just modifying the instance)
                # In a real hot-reload scenario, we might need `importlib.reload`.
                # For this MVP, we assume the patch is applied to disk. 
                # Re-instantiating the class *might* not pick up changes unless the module is reloaded.
                
                # MVP Strategy: Just retry. If the file changed, creating a new instance 
                # from the module MIGHT require module reload.
                # Let's delegate re-instantiation to the executor.
                new_impl = self.executor.reload_node_implementation(self.node_spec)
                self.inner = new_impl
                
                # Retry
                return await self.inner.execute(ctx)
            else:
                logger.warning("   ✗ Healing failed or declined.")
                return result
                
        except Exception as e:
            logger.error(f"   ☠ Critical failure during healing subsystem: {e}")
            logger.debug(traceback.format_exc())
            return result


class SelfHealingExecutor(GraphExecutor):
    """
    Executor that supports self-healing nodes.
    """
    def __init__(self, *args, evolve_on_failure: bool = False, **kwargs):
        super().__init__(*args, **kwargs)
        self.evolve_on_failure = evolve_on_failure

    def _get_node_implementation(self, node_spec: NodeSpec) -> NodeProtocol:
        # Get the standard implementation
        impl = super()._get_node_implementation(node_spec)
        # Wrap it
        return SelfHealingNodeWrapper(impl, self, node_spec)
        
    def reload_node_implementation(self, node_spec: NodeSpec) -> NodeProtocol:
        """Force reload of a node implementation (used after patching)."""
        # Remove from registry to force re-creation
        if node_spec.id in self.node_registry:
            del self.node_registry[node_spec.id]
            
        # TODO: Implement actual module reloading here
        # import importlib
        # import sys
        # ... logic to find the module and reload it ...
        
        return super()._get_node_implementation(node_spec)

    async def heal_node(
        self, 
        error: str, 
        node_spec: NodeSpec, 
        source_file: str, 
        context: NodeContext
    ) -> bool:
        """
        The core healing logic.
        1. Reads the source code.
        2. Uses LLM to diagnose and generate a patch.
        3. Applies the patch.
        """
        if not self.llm:
            logger.warning("   Cannot heal: No LLM available")
            return False
            
        try:
            # Read failing code
            with open(source_file, 'r', encoding='utf-8') as f:
                code_content = f.read()
                
            # Construct Meta-Agent Prompt
            prompt = f"""Use the provided error traceback and source code to identify and fix the bug.
            
NODE: {node_spec.name} ({node_spec.id})
ERROR: {error}

SOURCE CODE ({source_file}):
```python
{code_content}
```

INSTRUCTIONS:
1. Analyze why the error occurred.
2. Return the COMPLETE replacement content for the file.
3. Do not assume the user validation checks are wrong - usually the code logic is wrong.
4. Ensure imports remain intact.

Respond with ONLY the new file content inside a python code block."""

            # Call Meta-Agent
            print(f"   🤖 Asking Meta-Agent to fix {Path(source_file).name}...")
            response = self.llm.complete(
                messages=[{"role": "user", "content": prompt}],
                system="You are an expert Python debugger and software engineer. You fix bugs in agent code.",
                max_tokens=4000 # Enough for full file
            )
            
            # Extract code
            import re
            cleaned_text = response.content.strip()
            match = re.search(r"```python\s*\n?(.*?)\n?```", cleaned_text, re.DOTALL)
            if match:
                new_code = match.group(1)
            elif "def " in cleaned_text:
                new_code = cleaned_text # Raw code returned
            else:
                logger.warning("   Could not extract code from Meta-Agent response")
                return False
                
            # Verify it parses (safety check)
            import ast
            try:
                ast.parse(new_code)
            except SyntaxError as e:
                logger.error(f"   Generated patch has syntax error: {e}")
                return False
                
            # Apply Patch
            # Backup first
            backup_path = f"{source_file}.bak"
            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(code_content)
                
            # Write new code
            with open(source_file, 'w', encoding='utf-8') as f:
                f.write(new_code)
                
            logger.info(f"   ✓ Patched {source_file} (Backup: {backup_path})")
            return True

        except Exception as e:
            logger.error(f"   Healing failed: {e}")
            return False


class SelfHealingRunner(AgentRunner):
    """
    Agent Runner with Self-Healing capabilities.
    """
    def __init__(self, *args, evolve_on_failure: bool = False, **kwargs):
        super().__init__(*args, **kwargs)
        self.evolve_on_failure = evolve_on_failure

    def _setup_legacy_executor(self, tools: list, tool_executor: Callable | None) -> None:
        """Set up SelfHealingExecutor instead of GraphExecutor."""
        from framework.runtime.core import Runtime
        
        # Create runtime
        self._runtime = Runtime(storage_path=self._storage_path)

        # Create executor
        self._executor = SelfHealingExecutor(
            runtime=self._runtime,
            llm=self._llm,
            tools=tools,
            tool_executor=tool_executor,
            approval_callback=self._approval_callback,
            evolve_on_failure=self.evolve_on_failure
        )
