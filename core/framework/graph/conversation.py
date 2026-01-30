from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol, runtime_checkable
import json


@runtime_checkable
class ConversationStore(Protocol):
    """
    Minimal storage interface for write-through persistence.
    Implementations can wrap ConcurrentStorage, FileStorage, or any key-value backend.

    The key hierarchy is usually:
    {prefix}/meta.json   -> system_prompt, output_keys, config
    {prefix}/parts/{seq}.json -> individual messages, ordered by seq
    {prefix}/cursor.json -> iteration count, message count, timestamp
    """

    async def write_part(self, seq: int, data: dict) -> None:
        """Persist a single message part. Must be idempotent."""
        ...

    async def read_parts(self) -> list[dict]:
        """Read all parts in sequence order. Used by restore()."""
        ...

    async def write_meta(self, data: dict) -> None:
        """Persist conversation metadata (system prompt, config)."""
        ...

    async def read_meta(self) -> dict | None:
        """Read metadata. Returns None if no prior state."""
        ...

    async def write_cursor(self, data: dict) -> None:
        """Persist lightweight cursor (iteration, message count, timestamp)."""
        ...

    async def read_cursor(self) -> dict | None:
        """Read cursor. Returns None if no prior state."""
        ...

    async def delete_parts_before(self, seq: int) -> None:
        """Remove parts with seq < threshold. Used by compact()."""
        ...


@dataclass
class Message:
    seq: int  # monotonic sequence number
    role: str  # "system" | "user" | "assistant" | "tool"
    content: str
    tool_call_id: str | None = None
    tool_calls: list[dict[str, Any]] | None = None

    def to_llm_dict(self) -> dict[str, Any]:
        """Convert to format expected by LLMProvider.complete()."""
        d = {"role": self.role, "content": self.content}
        if self.tool_call_id:
            d["tool_call_id"] = self.tool_call_id
        if self.tool_calls:
            d["tool_calls"] = self.tool_calls
        return d

    def to_storage_dict(self) -> dict[str, Any]:
        """Serialize for ConversationStore.write_part()."""
        return {
            "seq": self.seq,
            "role": self.role,
            "content": self.content,
            "tool_call_id": self.tool_call_id,
            "tool_calls": self.tool_calls,
        }

    @classmethod
    def from_storage_dict(cls, data: dict[str, Any]) -> "Message":
        """Deserialize from stored part."""
        return cls(
            seq=data["seq"],
            role=data["role"],
            content=data["content"],
            tool_call_id=data.get("tool_call_id"),
            tool_calls=data.get("tool_calls"),
        )


class NodeConversation:
    def __init__(
        self,
        system_prompt: str = "",
        max_history_tokens: int = 32_000,
        compaction_threshold: float = 0.8,
        output_keys: list[str] | None = None,
        store: ConversationStore | None = None,
    ) -> None:
        self._system_prompt = system_prompt
        self._max_history_tokens = max_history_tokens
        self._compaction_threshold = compaction_threshold
        self._output_keys = output_keys or []
        self._store = store
        self._messages: list[Message] = []
        self._next_seq = 0

    @classmethod
    async def restore(
        cls,
        store: ConversationStore,
    ) -> "NodeConversation | None":
        """Rebuild conversation from stored parts. Returns None if store has no prior state."""
        meta = await store.read_meta()
        if meta is None:
            return None

        parts = await store.read_parts()
        conv = cls(
            system_prompt=meta.get("system_prompt", ""),
            max_history_tokens=meta.get("max_history_tokens", 32_000),
            compaction_threshold=meta.get("compaction_threshold", 0.8),
            output_keys=meta.get("output_keys", []),
            store=store,
        )

        for p in parts:
            msg = Message.from_storage_dict(p)
            conv._messages.append(msg)
            conv._next_seq = max(conv._next_seq, msg.seq + 1)

        return conv

    @property
    def system_prompt(self) -> str:
        return self._system_prompt

    @property
    def messages(self) -> list[Message]:
        return self._messages

    @property
    def turn_count(self) -> int:
        # Number of user messages
        return len([m for m in self._messages if m.role == "user"])

    @property
    def next_seq(self) -> int:
        return self._next_seq

    async def add_user_message(self, content: str) -> None:
        """Add user message. If store present, persists immediately."""
        msg = Message(seq=self._next_seq, role="user", content=content)
        self._messages.append(msg)
        self._next_seq += 1
        await self._persist(msg)

    async def add_assistant_message(
        self,
        content: str,
        tool_calls: list[dict[str, Any]] | None = None,
    ) -> None:
        """Add assistant message. If store present, persists immediately."""
        msg = Message(seq=self._next_seq, role="assistant", content=content, tool_calls=tool_calls)
        self._messages.append(msg)
        self._next_seq += 1
        await self._persist(msg)

    async def add_tool_result(
        self,
        tool_call_id: str,
        content: str,
        is_error: bool = False,
    ) -> None:
        """Add tool result. If store present, persists immediately."""
        msg = Message(seq=self._next_seq, role="tool", content=content, tool_call_id=tool_call_id)
        self._messages.append(msg)
        self._next_seq += 1
        await self._persist(msg)

    async def _persist(self, message: Message) -> None:
        """Write-through: store.write_part(). No-op if store is None."""
        if self._store:
            await self._store.write_part(message.seq, message.to_storage_dict())
            await self._store.write_cursor({
                "iteration": self.turn_count,
                "message_count": len(self._messages),
                "timestamp": datetime.now().isoformat(),
                "next_seq": self._next_seq
            })

    def to_llm_messages(self) -> list[dict[str, Any]]:
        """Export as list-of-dicts for LLMProvider.complete() (excludes system prompt)."""
        return [m.to_llm_dict() for m in self._messages]

    def estimate_tokens(self) -> int:
        """Rough estimate: 1 token ~ 4 characters."""
        total_chars = sum(len(m.content) for m in self._messages)
        return total_chars // 4

    def needs_compaction(self) -> bool:
        return self.estimate_tokens() >= (self._max_history_tokens * self._compaction_threshold)

    async def compact(self, summary: str) -> None:
        """
        Replace old messages with a summary, keep recent messages.
        Output-key-aware: extracts values for declared output_keys before discarding.
        """
        # Find compaction point: keep last 10% or at least 2 messages
        keep_count = max(2, len(self._messages) // 10)
        to_discard = self._messages[:-keep_count]
        to_keep = self._messages[-keep_count:]

        protected_values = self._extract_protected_values(to_discard)
        
        briefing = ""
        if protected_values:
            briefing += "PRESERVED VALUES (do not lose these):\n"
            for k, v in protected_values.items():
                briefing += f"- {k}: {v}\n"
            briefing += "\n"
        
        briefing += "CONVERSATION SUMMARY:\n"
        briefing += summary

        # Create summary message
        summary_msg = Message(
            seq=self._next_seq,
            role="assistant",
            content=briefing
        )
        self._next_seq += 1
        
        # New message list starts with summary
        self._messages = [summary_msg] + to_keep
        
        if self._store:
            # For a thorough implementation, we should replace history
            # But the spec says 'delete_parts_before' and write summary
            threshold = to_keep[0].seq if to_keep else self._next_seq
            await self._store.delete_parts_before(threshold)
            await self._store.write_part(summary_msg.seq, summary_msg.to_storage_dict())

    def _extract_protected_values(self, messages: list[Message]) -> dict[str, str]:
        """Scan messages for output_key values before compaction."""
        extracted = {}
        if not self._output_keys:
            return extracted

        import re
        for m in messages:
            if m.role != "assistant":
                continue
                
            for key in self._output_keys:
                # Patterns: "key: value", "key = value", {"key": value}
                patterns = [
                    rf'"{re.escape(key)}"\s*:\s*([^,}}\n]+)',
                    rf'{re.escape(key)}\s*:\s*([^\n]+)',
                    rf'{re.escape(key)}\s*=\s*([^\n]+)',
                ]
                for pattern in patterns:
                    match = re.search(pattern, m.content)
                    if match:
                        extracted[key] = match.group(1).strip()
        return extracted

    def export_summary(self) -> str:
        """Structured text summary for handoff to next node."""
        return f"CONVERSATION FROM NODE (Turns: {self.turn_count}, Tokens: ~{self.estimate_tokens()})\nMessages:\n" + "\n".join([f"{m.role}: {m.content[:100]}..." for m in self._messages])

    async def clear(self) -> None:
        """Clear messages, keep system prompt."""
        self._messages = []
        if self._store:
            await self._store.delete_parts_before(self._next_seq + 1)
