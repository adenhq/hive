"""Base policy protocol and abstract class.

Defines the interface that all policies must implement.
"""

from abc import ABC, abstractmethod
from typing import Protocol, runtime_checkable

from framework.policies.decisions import PolicyDecision
from framework.policies.events import PolicyEvent, PolicyEventType


@runtime_checkable
class Policy(Protocol):
    """Protocol defining the policy interface.

    All policies must implement this protocol to be registered
    with the PolicyEngine. The protocol defines:

    - id: Unique identifier for the policy
    - name: Human-readable name
    - description: What the policy does
    - event_types: Which events this policy evaluates
    - evaluate: Async method to evaluate an event

    Example:
        class MyPolicy:
            @property
            def id(self) -> str:
                return "my-policy"

            @property
            def name(self) -> str:
                return "My Custom Policy"

            @property
            def description(self) -> str:
                return "Checks for something important"

            @property
            def event_types(self) -> list[PolicyEventType]:
                return [PolicyEventType.TOOL_CALL]

            async def evaluate(self, event: PolicyEvent) -> PolicyDecision:
                return PolicyDecision.allow(self.id)
    """

    @property
    def id(self) -> str:
        """Unique identifier for this policy."""
        ...

    @property
    def name(self) -> str:
        """Human-readable name for this policy."""
        ...

    @property
    def description(self) -> str:
        """Description of what this policy does."""
        ...

    @property
    def event_types(self) -> list[PolicyEventType]:
        """Event types this policy evaluates."""
        ...

    async def evaluate(self, event: PolicyEvent) -> PolicyDecision:
        """Evaluate an event and return a decision.

        Args:
            event: The event to evaluate

        Returns:
            A PolicyDecision indicating what action to take
        """
        ...


class BasePolicy(ABC):
    """Abstract base class for policies.

    Provides a convenient base class with default implementations
    for common functionality. Subclasses must implement the abstract
    methods.

    Example:
        class MyPolicy(BasePolicy):
            @property
            def id(self) -> str:
                return "my-policy"

            @property
            def name(self) -> str:
                return "My Policy"

            @property
            def description(self) -> str:
                return "Does something useful"

            @property
            def event_types(self) -> list[PolicyEventType]:
                return [PolicyEventType.TOOL_CALL]

            async def evaluate(self, event: PolicyEvent) -> PolicyDecision:
                # Implementation here
                return PolicyDecision.allow(self.id)
    """

    @property
    @abstractmethod
    def id(self) -> str:
        """Unique identifier for this policy."""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name for this policy."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Description of what this policy does."""
        pass

    @property
    @abstractmethod
    def event_types(self) -> list[PolicyEventType]:
        """Event types this policy evaluates."""
        pass

    @abstractmethod
    async def evaluate(self, event: PolicyEvent) -> PolicyDecision:
        """Evaluate an event and return a decision.

        Args:
            event: The event to evaluate

        Returns:
            A PolicyDecision indicating what action to take
        """
        pass

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(id={self.id!r}, name={self.name!r})"
