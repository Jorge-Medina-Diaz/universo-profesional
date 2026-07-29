"""Sanitise the message payload agno sends to the Anthropic Messages API.

**Why this exists.** agno 2.6.8's `format_messages`
(`agno/utils/models/claude.py`) builds the Anthropic request from the agno
message list. For a user/forwarded message it does `content = message.content
or ""` and wraps it as `[{"type": "text", "text": ""}]` when the content is
empty — which happens routinely during `mode="route"` task hand-offs between a
team coordinator and its members. Anthropic rejects the *entire* request with
``messages: text content blocks must be non-empty``, so roughly half the chat
turns 400 with no user-visible error.

Rather than fork agno, we wrap the single bound name
`agno.models.anthropic.claude.format_messages` (used by all six invoke paths)
and strip/repair empty blocks from its output before it reaches the API:

  * empty ``text`` blocks are dropped,
  * empty ``tool_result`` content is replaced with a ``(sin salida)`` placeholder,
  * messages whose content becomes empty are dropped (or, for the trailing
    user turn, replaced with a ``continúa`` placeholder so the request stays
    valid), and
  * consecutive same-role messages are re-merged to preserve alternation.

Pinned to agno 2.6.x — defensive enough to tolerate minor version bumps, but
re-verify if agno is upgraded.
"""
from __future__ import annotations

from typing import Any

from agno.utils.log import log_warning

_INSTALLED = False
_EMPTY_TOOL_RESULT = "(sin salida)"
_EMPTY_USER_FILLER = "continúa"


def _block_attr(block: Any, key: str) -> Any:
    """Read a field from a content block that may be a dict or an SDK object."""
    if isinstance(block, dict):
        return block.get(key)
    return getattr(block, key, None)


def _is_blank(value: Any) -> bool:
    if value is None:
        return True
    text = str(value).strip()
    return text in ("", "None")


def _fix_tool_result_content(inner: Any) -> Any | None:
    """Return a replacement for a tool_result's ``content``, or None to keep it.

    Anthropic rejects a tool_result whose content is an empty string or which
    contains empty text blocks, so we normalise both shapes.
    """
    if isinstance(inner, str):
        return _EMPTY_TOOL_RESULT if _is_blank(inner) else None
    if isinstance(inner, list):
        kept = [
            b
            for b in inner
            if not (_block_attr(b, "type") == "text" and _is_blank(_block_attr(b, "text")))
        ]
        if not kept:
            return [{"type": "text", "text": _EMPTY_TOOL_RESULT}]
        return kept if len(kept) != len(inner) else None
    if inner is None:
        return _EMPTY_TOOL_RESULT
    return None


def _sanitise_content_list(content: list[Any]) -> list[Any]:
    out: list[Any] = []
    for block in content:
        btype = _block_attr(block, "type")
        if btype == "text" and _is_blank(_block_attr(block, "text")):
            continue  # empty text block → Anthropic 400
        if btype == "tool_result":
            fixed = _fix_tool_result_content(_block_attr(block, "content"))
            if fixed is not None:
                if isinstance(block, dict):
                    out.append({**block, "content": fixed})
                    continue
                # SDK object (not a dict): the old code kept it unchanged, so
                # the repaired content was silently discarded and Anthropic
                # still received the empty tool_result this sanitiser exists
                # to prevent. Rebuild as a plain dict, preserving the linking
                # tool_use_id and error flag.
                rebuilt: dict[str, Any] = {"type": "tool_result", "content": fixed}
                tool_use_id = _block_attr(block, "tool_use_id")
                if tool_use_id is not None:
                    rebuilt["tool_use_id"] = tool_use_id
                is_error = _block_attr(block, "is_error")
                if is_error is not None:
                    rebuilt["is_error"] = is_error
                out.append(rebuilt)
                continue
        out.append(block)
    return out


def _merge_consecutive(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Re-merge adjacent same-role messages (dropping a turn can break it)."""
    merged: list[dict[str, Any]] = []
    for msg in messages:
        if merged and merged[-1].get("role") == msg.get("role"):
            prev, curr = merged[-1].get("content"), msg.get("content")
            prev_list = prev if isinstance(prev, list) else [{"type": "text", "text": str(prev)}]
            curr_list = curr if isinstance(curr, list) else [{"type": "text", "text": str(curr)}]
            merged[-1] = {**merged[-1], "content": prev_list + curr_list}
        else:
            merged.append(msg)
    return merged


def _sanitise_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cleaned: list[dict[str, Any]] = []
    dropped = 0
    blocks_fixed = 0
    for msg in messages:
        role = msg.get("role")
        content = msg.get("content")

        if isinstance(content, list):
            new_content: Any = _sanitise_content_list(content)
            if len(new_content) != len(content):
                blocks_fixed += len(content) - len(new_content)
            if not new_content:
                if role == "user":
                    new_content = [{"type": "text", "text": _EMPTY_USER_FILLER}]
                else:
                    dropped += 1
                    continue
            cleaned.append({**msg, "content": new_content})
            continue

        # String / None content.
        if _is_blank(content):
            blocks_fixed += 1
            if role == "user":
                cleaned.append({**msg, "content": _EMPTY_USER_FILLER})
            else:
                dropped += 1
            continue
        cleaned.append(msg)

    cleaned = _merge_consecutive(cleaned)

    # Anthropic requires a non-empty trailing turn; guarantee it.
    if cleaned and _is_blank_message(cleaned[-1]):
        cleaned[-1] = {**cleaned[-1], "content": [{"type": "text", "text": _EMPTY_USER_FILLER}]}

    if dropped or blocks_fixed or len(cleaned) != len(messages):
        log_warning(
            f"anthropic_sanitize: repaired payload "
            f"({len(messages)}→{len(cleaned)} messages, {dropped} dropped, "
            f"{blocks_fixed} empty blocks fixed)"
        )
    return cleaned


def _is_blank_message(msg: dict[str, Any]) -> bool:
    content = msg.get("content")
    if isinstance(content, list):
        return len(content) == 0
    return _is_blank(content)


def install_anthropic_sanitizer() -> None:
    """Idempotently wrap ``format_messages`` in the agno Anthropic model module."""
    global _INSTALLED
    if _INSTALLED:
        return
    try:
        from agno.models.anthropic import claude as claude_mod
    except Exception:  # pragma: no cover - agno not installed / mock provider
        return

    original = claude_mod.format_messages

    def _patched(*args: Any, **kwargs: Any):  # type: ignore[no-untyped-def]
        chat_messages, system_prompt = original(*args, **kwargs)
        try:
            chat_messages = _sanitise_messages(chat_messages)
        except Exception as exc:  # never let sanitisation break a real request
            log_warning(f"anthropic_sanitize: skipped (error: {exc})")
        return chat_messages, system_prompt

    _patched.__wrapped__ = original  # type: ignore[attr-defined]
    claude_mod.format_messages = _patched

    # P1.E: agno's _apply_cache_tools hardcodes {"type": "ephemeral"} (5m).
    # With model-level extended_cache_time=True the SYSTEM block carries
    # ttl='1h', and Anthropic rejects a 1h block AFTER a 5m one (blocks are
    # processed tools → system → messages). Honor the flag on the tools
    # block too — the 47-tool schema is the largest stable prefix we cache.
    original_cache_tools = claude_mod.Claude._apply_cache_tools

    def _patched_cache_tools(self: Any, request_kwargs: dict[str, Any]) -> None:
        original_cache_tools(self, request_kwargs)
        if (
            getattr(self, "extended_cache_time", False)
            and self.cache_tools
            and request_kwargs.get("tools")
        ):
            request_kwargs["tools"][-1]["cache_control"] = {
                "type": "ephemeral",
                "ttl": "1h",
            }

    _patched_cache_tools.__wrapped__ = original_cache_tools  # type: ignore[attr-defined]
    claude_mod.Claude._apply_cache_tools = _patched_cache_tools
    _INSTALLED = True
