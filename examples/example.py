"""
Comprehensive Feature Examples - Easy, Medium, Hard
====================================================

This module demonstrates the Hive agent framework capabilities
at three complexity levels: Easy, Medium, and Hard.

Each level progressively introduces more advanced concepts:
- Easy: Basic tool usage, simple validation
- Medium: Multi-agent selection, complex validation, error handling
- Hard: Async execution, caching, monitoring, priority-based routing

Run this file directly:
    cd c:\\Users\\M.S.Seshashayanan\\Desktop\\Aden\\hive
    python examples/example.py

Or import individual examples:
    from examples.example import run_easy_example
    run_easy_example()
"""

import os
import sys
import asyncio
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# Add project paths
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "tools" / "src"))

# Clear proxy settings
os.environ["HTTP_PROXY"] = ""
os.environ["HTTPS_PROXY"] = ""

# Load environment
from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

# Import tools
from fastmcp import FastMCP
from aden_tools.tools import register_all_tools


# =============================================================================
# SHARED UTILITIES
# =============================================================================

class Priority(Enum):
    """Task priority levels."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class ValidationResult:
    """Result of input validation."""
    valid: bool
    errors: List[str]
    warnings: List[str]
    
    def __bool__(self):
        return self.valid


def get_tools():
    """Initialize and return MCP tools."""
    mcp = FastMCP("examples")
    tools = register_all_tools(mcp)
    
    def get_tool(name: str) -> Callable:
        return mcp._tool_manager._tools[name].fn
    
    return get_tool, tools


# =============================================================================
# EASY EXAMPLE - Basic Usage
# =============================================================================
"""
EASY LEVEL
----------
Demonstrates:
- Basic tool initialization
- Simple input validation
- Single tool execution
- Straightforward result handling

Use cases:
- Create a support ticket
- Look up a contact
- Send a notification

Validation:
- Required field checks
- Basic type validation
"""


def validate_easy(data: Dict[str, Any]) -> ValidationResult:
    """
    Simple validation for easy example.
    
    Rules:
    - title is required and non-empty
    - priority must be valid if provided
    """
    errors = []
    warnings = []
    
    # Required field check
    if not data.get("title"):
        errors.append("title is required")
    elif len(data["title"]) < 3:
        errors.append("title must be at least 3 characters")
    
    # Priority validation
    valid_priorities = ["low", "medium", "high", "critical"]
    if data.get("priority") and data["priority"] not in valid_priorities:
        errors.append(f"priority must be one of: {valid_priorities}")
    
    # Optional warnings
    if not data.get("description"):
        warnings.append("description is recommended for better tracking")
    
    return ValidationResult(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings
    )


def run_easy_example():
    """
    EASY EXAMPLE: Create a simple support ticket.
    
    Steps:
    1. Initialize tools
    2. Validate input
    3. Create ticket
    4. Display result
    
    Input:
        title: str (required)
        description: str (optional)
        priority: str (optional, default: "medium")
    
    Output:
        ticket_id: str
        status: str
        created_at: str
    """
    print("\n" + "=" * 70)
    print("EASY EXAMPLE: Create a Support Ticket")
    print("=" * 70 + "\n")
    
    # Step 1: Initialize tools
    logger.info("Initializing tools...")
    get_tool, tools = get_tools()
    logger.info(f"Loaded {len(tools)} tools")
    
    # Step 2: Prepare input data
    input_data = {
        "title": "Login page not loading",
        "description": "Users report blank page on /login endpoint",
        "priority": "high"
    }
    
    # Step 3: Validate input
    logger.info("Validating input...")
    validation = validate_easy(input_data)
    
    if not validation:
        for error in validation.errors:
            logger.error(f"Validation error: {error}")
        return None
    
    for warning in validation.warnings:
        logger.warning(f"Validation warning: {warning}")
    
    logger.info("Validation passed!")
    
    # Step 4: Execute tool
    logger.info("Creating ticket...")
    result = get_tool("create_ticket")(
        title=input_data["title"],
        description=input_data.get("description", ""),
        priority=input_data.get("priority", "medium")
    )
    
    # Step 5: Handle result
    if result.get("success"):
        logger.info(f"Ticket created successfully!")
        print(f"\n  Ticket ID: {result.get('ticket_id')}")
        print(f"  Status: {result.get('ticket', {}).get('status', 'open')}")
        print(f"  Priority: {input_data['priority']}")
        return result
    else:
        logger.error(f"Failed to create ticket: {result.get('error')}")
        return None


# =============================================================================
# MEDIUM EXAMPLE - Multi-Agent Selection
# =============================================================================
"""
MEDIUM LEVEL
------------
Demonstrates:
- Multiple agent/tool selection based on input type
- Complex validation with custom rules
- Error handling with retry logic
- Configuration-driven behavior

Use cases:
- Route customer requests to appropriate team
- Process different types of data with specialized tools
- Handle partial failures gracefully

Validation:
- Multi-field validation
- Cross-field validation rules
- Custom validation functions

Agent Selection:
- Rule-based routing
- Input type detection
- Priority-based selection
"""


@dataclass
class AgentConfig:
    """Configuration for an agent."""
    name: str
    tool: str
    priority: int
    supports: List[str]
    max_retries: int = 3


# Agent registry with capabilities
AGENTS = {
    "ticket_agent": AgentConfig(
        name="Ticket Handler",
        tool="create_ticket",
        priority=1,
        supports=["ticket", "issue", "bug", "request"]
    ),
    "crm_agent": AgentConfig(
        name="CRM Handler", 
        tool="crm_create_contact",
        priority=1,
        supports=["contact", "customer", "lead", "account"]
    ),
    "notification_agent": AgentConfig(
        name="Notification Handler",
        tool="send_notification",
        priority=2,
        supports=["alert", "notify", "message", "email"]
    )
}


def validate_medium(data: Dict[str, Any]) -> ValidationResult:
    """
    Complex validation for medium example.
    
    Rules:
    - request_type must be valid
    - data must contain required fields for type
    - cross-field validation
    """
    errors = []
    warnings = []
    
    request_type = data.get("request_type", "").lower()
    
    # Type validation
    valid_types = ["ticket", "contact", "notification"]
    if not request_type:
        errors.append("request_type is required")
    elif request_type not in valid_types:
        errors.append(f"request_type must be one of: {valid_types}")
    
    # Type-specific validation
    if request_type == "ticket":
        if not data.get("title"):
            errors.append("title is required for ticket requests")
    
    elif request_type == "contact":
        if not data.get("name"):
            errors.append("name is required for contact requests")
        if not data.get("email"):
            warnings.append("email is recommended for contacts")
    
    elif request_type == "notification":
        if not data.get("recipient"):
            errors.append("recipient is required for notifications")
        if not data.get("message"):
            errors.append("message is required for notifications")
    
    return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)


def select_agent(request_type: str) -> Optional[AgentConfig]:
    """
    Select the appropriate agent based on request type.
    
    Selection criteria:
    1. Match request_type to agent's supported types
    2. If multiple matches, select by priority
    3. Return None if no agent supports the type
    """
    candidates = []
    
    for agent_id, config in AGENTS.items():
        for supported in config.supports:
            if request_type.lower() in supported or supported in request_type.lower():
                candidates.append((agent_id, config))
                break
    
    if not candidates:
        return None
    
    # Sort by priority (lower is better)
    candidates.sort(key=lambda x: x[1].priority)
    return candidates[0][1]


def execute_with_retry(
    tool_fn: Callable, 
    params: Dict[str, Any],
    max_retries: int = 3,
    delay: float = 1.0
) -> Dict[str, Any]:
    """
    Execute a tool with retry logic.
    
    Retry conditions:
    - Network errors
    - Temporary failures
    - Rate limiting
    
    Not retried:
    - Validation errors
    - Permission errors
    - Resource not found
    """
    import time
    
    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            result = tool_fn(**params)
            
            if result.get("success"):
                return result
            
            # Check if error is retryable
            error = result.get("error", "")
            if any(x in error.lower() for x in ["timeout", "rate limit", "temporary"]):
                last_error = error
                logger.warning(f"Attempt {attempt} failed (retryable): {error}")
                time.sleep(delay * attempt)  # Exponential backoff
                continue
            
            # Non-retryable error
            return result
            
        except Exception as e:
            last_error = str(e)
            logger.warning(f"Attempt {attempt} exception: {e}")
            time.sleep(delay * attempt)
    
    return {"success": False, "error": f"Max retries exceeded: {last_error}"}


def run_medium_example():
    """
    MEDIUM EXAMPLE: Multi-agent request routing.
    
    Steps:
    1. Validate the incoming request
    2. Select appropriate agent based on request type
    3. Execute with retry logic
    4. Handle errors gracefully
    
    Input:
        request_type: str ("ticket", "contact", "notification")
        ...type-specific fields
    
    Output:
        agent_used: str
        result: dict
        attempts: int
    """
    print("\n" + "=" * 70)
    print("MEDIUM EXAMPLE: Multi-Agent Request Routing")
    print("=" * 70 + "\n")
    
    # Step 1: Initialize
    logger.info("Initializing tools...")
    get_tool, tools = get_tools()
    
    # Step 2: Example requests to process
    requests = [
        {"request_type": "ticket", "title": "API returning 500 errors", "priority": "high"},
        {"request_type": "contact", "name": "Jane Doe", "email": "jane@company.com"},
        {"request_type": "notification", "recipient": "team@company.com", "message": "Deploy complete"}
    ]
    
    results = []
    
    for i, request in enumerate(requests, 1):
        print(f"\n--- Request {i}: {request['request_type'].upper()} ---")
        
        # Validate
        validation = validate_medium(request)
        if not validation:
            logger.error(f"Validation failed: {validation.errors}")
            continue
        
        # Select agent
        agent = select_agent(request["request_type"])
        if not agent:
            logger.error(f"No agent found for type: {request['request_type']}")
            continue
        
        logger.info(f"Selected agent: {agent.name}")
        
        # Prepare parameters based on request type
        if request["request_type"] == "ticket":
            params = {"title": request["title"], "description": request.get("description", ""), "priority": request.get("priority", "medium")}
        elif request["request_type"] == "contact":
            params = {"name": request["name"], "email": request.get("email", "")}
        elif request["request_type"] == "notification":
            params = {"recipient": request["recipient"], "message": request["message"], "channel": "email"}
        
        # Execute with retry
        result = execute_with_retry(
            get_tool(agent.tool),
            params,
            max_retries=agent.max_retries
        )
        
        if result.get("success"):
            logger.info(f"Success! Result: {result.get('ticket_id') or result.get('contact_id') or result.get('notification_id')}")
        else:
            logger.error(f"Failed: {result.get('error')}")
        
        results.append({
            "request": request,
            "agent": agent.name,
            "result": result
        })
    
    print(f"\n\nProcessed {len(results)} requests")
    return results


# =============================================================================
# HARD EXAMPLE - Advanced Async Pipeline
# =============================================================================
"""
HARD LEVEL
----------
Demonstrates:
- Asynchronous execution with callbacks
- Dynamic agent selection with scoring
- Multi-stage validation pipeline
- Caching for performance
- Monitoring and metrics
- Edge case handling
- Fallback strategies

Use cases:
- High-throughput request processing
- Complex multi-step workflows
- Real-time monitoring and alerting
- Resilient distributed systems

Validation:
- Schema validation
- Business rule validation
- Security validation
- Rate limiting validation

Agent Selection:
- Score-based routing
- Load balancing
- Capability matching
- Fallback chains
"""


@dataclass
class AgentScore:
    """Score for agent selection."""
    agent_id: str
    score: float
    reasons: List[str]


@dataclass
class PipelineStage:
    """A stage in the validation/execution pipeline."""
    name: str
    validator: Callable
    required: bool = True


class SimpleCache:
    """Simple in-memory cache with TTL."""
    
    def __init__(self, ttl_seconds: int = 300):
        self.cache: Dict[str, tuple] = {}
        self.ttl = ttl_seconds
    
    def get(self, key: str) -> Optional[Any]:
        if key in self.cache:
            value, timestamp = self.cache[key]
            if (datetime.now() - timestamp).seconds < self.ttl:
                return value
            del self.cache[key]
        return None
    
    def set(self, key: str, value: Any) -> None:
        self.cache[key] = (value, datetime.now())
    
    def clear(self) -> None:
        self.cache.clear()


class Metrics:
    """Simple metrics collector."""
    
    def __init__(self):
        self.counters: Dict[str, int] = {}
        self.timers: Dict[str, List[float]] = {}
        self.start_time = datetime.now()
    
    def increment(self, name: str, value: int = 1) -> None:
        self.counters[name] = self.counters.get(name, 0) + value
    
    def record_time(self, name: str, duration: float) -> None:
        if name not in self.timers:
            self.timers[name] = []
        self.timers[name].append(duration)
    
    def get_summary(self) -> Dict[str, Any]:
        return {
            "duration_seconds": (datetime.now() - self.start_time).seconds,
            "counters": self.counters,
            "avg_times": {k: sum(v)/len(v) for k, v in self.timers.items() if v}
        }


class AdvancedPipeline:
    """
    Advanced async processing pipeline.
    
    Features:
    - Multi-stage validation
    - Score-based agent selection
    - Async execution with callbacks
    - Caching and metrics
    - Fallback handling
    """
    
    def __init__(self):
        self.get_tool, self.tools = get_tools()
        self.cache = SimpleCache(ttl_seconds=300)
        self.metrics = Metrics()
        self.callbacks: List[Callable] = []
    
    def add_callback(self, callback: Callable) -> None:
        """Add a callback to be invoked on events."""
        self.callbacks.append(callback)
    
    def _notify_callbacks(self, event: str, data: Any) -> None:
        """Notify all callbacks of an event."""
        for callback in self.callbacks:
            try:
                callback(event, data)
            except Exception as e:
                logger.warning(f"Callback error: {e}")
    
    def validate_schema(self, data: Dict) -> ValidationResult:
        """Stage 1: Schema validation."""
        errors = []
        
        required = ["type", "payload"]
        for field in required:
            if field not in data:
                errors.append(f"Missing required field: {field}")
        
        return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=[])
    
    def validate_business(self, data: Dict) -> ValidationResult:
        """Stage 2: Business rule validation."""
        errors = []
        warnings = []
        
        payload = data.get("payload", {})
        request_type = data.get("type", "")
        
        # Business rules
        if request_type == "ticket" and payload.get("priority") == "critical":
            if not payload.get("escalation_contact"):
                warnings.append("Critical tickets should have escalation_contact")
        
        if request_type == "contact" and "@" in payload.get("email", ""):
            domain = payload["email"].split("@")[1]
            if domain in ["test.com", "example.com"]:
                warnings.append("Test/example email domains detected")
        
        return ValidationResult(valid=True, errors=errors, warnings=warnings)
    
    def validate_security(self, data: Dict) -> ValidationResult:
        """Stage 3: Security validation."""
        errors = []
        
        payload = data.get("payload", {})
        
        # Check for potential injection
        for key, value in payload.items():
            if isinstance(value, str):
                dangerous = ["<script>", "DROP TABLE", "DELETE FROM", "eval("]
                if any(d.lower() in value.lower() for d in dangerous):
                    errors.append(f"Potential security issue in field: {key}")
        
        return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=[])
    
    def run_validation_pipeline(self, data: Dict) -> ValidationResult:
        """Run all validation stages."""
        stages = [
            PipelineStage("schema", self.validate_schema, required=True),
            PipelineStage("business", self.validate_business, required=False),
            PipelineStage("security", self.validate_security, required=True),
        ]
        
        all_errors = []
        all_warnings = []
        
        for stage in stages:
            start = datetime.now()
            result = stage.validator(data)
            duration = (datetime.now() - start).total_seconds()
            
            self.metrics.record_time(f"validation_{stage.name}", duration)
            
            all_warnings.extend(result.warnings)
            
            if not result.valid:
                all_errors.extend(result.errors)
                if stage.required:
                    logger.error(f"Required validation failed: {stage.name}")
                    break
        
        return ValidationResult(
            valid=len(all_errors) == 0,
            errors=all_errors,
            warnings=all_warnings
        )
    
    def score_agent(self, agent: AgentConfig, data: Dict) -> AgentScore:
        """
        Calculate a score for agent selection.
        
        Scoring factors:
        - Type match: +10 for exact, +5 for partial
        - Priority alignment: +3 for high priority agents on critical requests
        - Load (simulated): -2 for high load
        - Success rate (simulated): +5 for high success rate
        """
        score = 0.0
        reasons = []
        
        request_type = data.get("type", "").lower()
        
        # Type match
        for supported in agent.supports:
            if supported == request_type:
                score += 10
                reasons.append("Exact type match")
                break
            elif supported in request_type or request_type in supported:
                score += 5
                reasons.append("Partial type match")
                break
        
        # Priority alignment
        payload = data.get("payload", {})
        if payload.get("priority") in ["high", "critical"] and agent.priority == 1:
            score += 3
            reasons.append("Priority agent for urgent request")
        
        # Simulated load factor
        import random
        load = random.random()
        if load > 0.8:
            score -= 2
            reasons.append("Agent under high load")
        
        # Simulated success rate
        success_rate = random.uniform(0.7, 1.0)
        if success_rate > 0.9:
            score += 5
            reasons.append("High historical success rate")
        
        return AgentScore(agent_id=agent.name, score=score, reasons=reasons)
    
    def select_best_agent(self, data: Dict) -> Optional[AgentConfig]:
        """Select the best agent based on scoring."""
        scores = []
        
        for agent_id, agent in AGENTS.items():
            score = self.score_agent(agent, data)
            scores.append((agent, score))
            logger.debug(f"Agent {agent.name}: score={score.score:.2f}, reasons={score.reasons}")
        
        # Sort by score descending
        scores.sort(key=lambda x: x[1].score, reverse=True)
        
        if scores and scores[0][1].score > 0:
            winner = scores[0]
            logger.info(f"Selected: {winner[0].name} (score: {winner[1].score:.2f})")
            return winner[0]
        
        return None
    
    async def execute_async(
        self, 
        data: Dict,
        timeout: float = 30.0
    ) -> Dict[str, Any]:
        """
        Execute request with async support.
        
        Features:
        - Timeout handling
        - Callback notifications
        - Metrics collection
        - Cache checking
        """
        import hashlib
        import json
        
        # Generate cache key
        cache_key = hashlib.md5(json.dumps(data, sort_keys=True).encode()).hexdigest()
        
        # Check cache
        cached = self.cache.get(cache_key)
        if cached:
            self.metrics.increment("cache_hits")
            logger.info("Cache hit!")
            return cached
        
        self.metrics.increment("cache_misses")
        
        # Notify start
        self._notify_callbacks("start", {"data": data})
        
        start_time = datetime.now()
        
        try:
            # Run validation
            validation = self.run_validation_pipeline(data)
            if not validation:
                self.metrics.increment("validation_failures")
                return {"success": False, "errors": validation.errors}
            
            for warning in validation.warnings:
                logger.warning(f"Validation warning: {warning}")
            
            # Select agent
            agent = self.select_best_agent(data)
            if not agent:
                self.metrics.increment("no_agent_found")
                return {"success": False, "error": "No suitable agent found"}
            
            # Prepare params
            payload = data.get("payload", {})
            request_type = data.get("type", "")
            
            if request_type == "ticket":
                params = {
                    "title": payload.get("title", "Untitled"),
                    "priority": payload.get("priority", "medium"),
                    "description": payload.get("description", "")
                }
            elif request_type == "contact":
                params = {
                    "name": payload.get("name", "Unknown"),
                    "email": payload.get("email", ""),
                    "company": payload.get("company", "")
                }
            else:
                params = payload
            
            # Execute with timeout simulation
            result = self.get_tool(agent.tool)(**params)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            self.metrics.record_time("execution", execution_time)
            
            if result.get("success"):
                self.metrics.increment("success")
                self.cache.set(cache_key, result)
            else:
                self.metrics.increment("failures")
            
            # Notify complete
            self._notify_callbacks("complete", {
                "data": data,
                "result": result,
                "duration": execution_time
            })
            
            return {
                "success": result.get("success", False),
                "agent": agent.name,
                "result": result,
                "execution_time": execution_time
            }
            
        except asyncio.TimeoutError:
            self.metrics.increment("timeouts")
            return {"success": False, "error": "Execution timeout"}
        except Exception as e:
            self.metrics.increment("exceptions")
            logger.error(f"Pipeline exception: {e}")
            return {"success": False, "error": str(e)}
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get collected metrics."""
        return self.metrics.get_summary()


def run_hard_example():
    """
    HARD EXAMPLE: Advanced async pipeline with monitoring.
    
    Steps:
    1. Initialize pipeline with caching and metrics
    2. Add event callbacks for monitoring
    3. Run multiple requests through validation pipeline
    4. Use score-based agent selection
    5. Execute with async support
    6. Generate metrics report
    
    Features demonstrated:
    - Multi-stage validation pipeline
    - Score-based agent selection
    - Request caching
    - Metrics collection
    - Event callbacks
    - Error handling and fallbacks
    """
    print("\n" + "=" * 70)
    print("HARD EXAMPLE: Advanced Async Pipeline")
    print("=" * 70 + "\n")
    
    # Step 1: Initialize pipeline
    logger.info("Initializing advanced pipeline...")
    pipeline = AdvancedPipeline()
    
    # Step 2: Add monitoring callback
    def monitor_callback(event: str, data: Any):
        if event == "start":
            logger.info(f"[MONITOR] Processing started")
        elif event == "complete":
            logger.info(f"[MONITOR] Completed in {data['duration']:.3f}s")
    
    pipeline.add_callback(monitor_callback)
    
    # Step 3: Prepare test requests
    requests = [
        {
            "type": "ticket",
            "payload": {
                "title": "Critical: Database connection pool exhausted",
                "priority": "critical",
                "description": "Production database showing connection errors"
            }
        },
        {
            "type": "contact", 
            "payload": {
                "name": "Alice Johnson",
                "email": "alice@enterprise.com",
                "company": "Enterprise Corp"
            }
        },
        {
            "type": "ticket",
            "payload": {
                "title": "Minor UI alignment issue",
                "priority": "low",
                "description": "Button slightly off-center on mobile"
            }
        },
        # Duplicate to test caching
        {
            "type": "ticket",
            "payload": {
                "title": "Critical: Database connection pool exhausted",
                "priority": "critical",
                "description": "Production database showing connection errors"
            }
        },
        # Edge case: Invalid request
        {
            "type": "unknown",
            "payload": {}
        }
    ]
    
    # Step 4: Process all requests
    async def process_all():
        results = []
        for i, request in enumerate(requests, 1):
            print(f"\n--- Request {i}/{len(requests)} ---")
            logger.info(f"Type: {request['type']}")
            
            result = await pipeline.execute_async(request)
            results.append(result)
            
            if result.get("success"):
                logger.info(f"Success via {result.get('agent')}")
            else:
                logger.warning(f"Failed: {result.get('error') or result.get('errors')}")
        
        return results
    
    # Run async
    results = asyncio.run(process_all())
    
    # Step 5: Generate report
    print("\n" + "=" * 70)
    print("METRICS REPORT")
    print("=" * 70)
    
    metrics = pipeline.get_metrics()
    
    print(f"\nDuration: {metrics['duration_seconds']} seconds")
    print(f"\nCounters:")
    for name, value in metrics['counters'].items():
        print(f"  {name}: {value}")
    
    print(f"\nAverage Times:")
    for name, avg in metrics.get('avg_times', {}).items():
        print(f"  {name}: {avg*1000:.2f}ms")
    
    print(f"\nResults Summary:")
    successes = sum(1 for r in results if r.get("success"))
    print(f"  Total: {len(results)}")
    print(f"  Success: {successes}")
    print(f"  Failed: {len(results) - successes}")
    
    return {
        "results": results,
        "metrics": metrics
    }


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def main():
    """Run all examples."""
    print("\n" + "#" * 70)
    print("#" + " " * 68 + "#")
    print("#  HIVE COMPREHENSIVE EXAMPLES - Easy, Medium, Hard" + " " * 17 + "#")
    print("#" + " " * 68 + "#")
    print("#" * 70)
    
    # Run Easy Example
    print("\n\n" + "~" * 70)
    print("RUNNING EASY EXAMPLE")
    print("~" * 70)
    run_easy_example()
    
    # Run Medium Example
    print("\n\n" + "~" * 70)
    print("RUNNING MEDIUM EXAMPLE")
    print("~" * 70)
    run_medium_example()
    
    # Run Hard Example
    print("\n\n" + "~" * 70)
    print("RUNNING HARD EXAMPLE")
    print("~" * 70)
    run_hard_example()
    
    print("\n\n" + "#" * 70)
    print("#" + " " * 68 + "#")
    print("#  ALL EXAMPLES COMPLETE" + " " * 44 + "#")
    print("#" + " " * 68 + "#")
    print("#" * 70 + "\n")


if __name__ == "__main__":
    main()
