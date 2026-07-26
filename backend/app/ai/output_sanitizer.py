import re


THINK_BLOCK_PATTERN = re.compile(r"(?is)<think\b[^>]*>.*?</think>")
DANGLING_THINK_PATTERN = re.compile(r"(?is)<think\b[^>]*>.*$")
CLOSING_THINK_PATTERN = re.compile(r"(?is)</think>")


def strip_reasoning_text(text: str) -> str:
    """Remove model reasoning blocks from user-visible output."""

    cleaned = THINK_BLOCK_PATTERN.sub("", text)
    cleaned = DANGLING_THINK_PATTERN.sub("", cleaned)
    cleaned = CLOSING_THINK_PATTERN.sub("", cleaned)
    return cleaned.strip()


class ReasoningStreamFilter:
    """Hide streamed <think>...</think> blocks while preserving visible text."""

    _tag_prefix_keep = len("<think")

    def __init__(self) -> None:
        self._buffer = ""
        self._inside_think = False

    def feed(self, chunk: str) -> str:
        self._buffer += chunk
        visible_parts: list[str] = []

        while self._buffer:
            lower = self._buffer.lower()
            if self._inside_think:
                end = lower.find("</think>")
                if end < 0:
                    keep = len("</think>") - 1
                    self._buffer = self._buffer[-keep:]
                    break
                self._buffer = self._buffer[end + len("</think>") :]
                self._inside_think = False
                continue

            start = lower.find("<think")
            if start < 0:
                possible_tag_start = self._buffer.rfind("<")
                if (
                    possible_tag_start >= 0
                    and len(self._buffer) - possible_tag_start
                    <= self._tag_prefix_keep
                ):
                    visible_parts.append(self._buffer[:possible_tag_start])
                    self._buffer = self._buffer[possible_tag_start:]
                    break
                visible_parts.append(self._buffer)
                self._buffer = ""
                break

            visible_parts.append(self._buffer[:start])
            tag_end = lower.find(">", start)
            if tag_end < 0:
                self._buffer = self._buffer[start:]
                break
            self._buffer = self._buffer[tag_end + 1 :]
            self._inside_think = True

        return "".join(visible_parts)

    def flush(self) -> str:
        if self._inside_think:
            self._buffer = ""
            self._inside_think = False
            return ""
        visible = strip_reasoning_text(self._buffer)
        self._buffer = ""
        return visible
