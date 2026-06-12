from dataclasses import dataclass


@dataclass(frozen=True)
class TextChunk:
    """A text chunk with its original line range."""

    content: str
    start_line: int
    end_line: int


def chunk_text(text: str, max_chars: int = 2000) -> list[TextChunk]:
    """Split text into line-aware chunks no larger than max_chars."""

    if max_chars <= 0:
        raise ValueError("max_chars must be greater than zero.")

    lines = text.splitlines()
    chunks: list[TextChunk] = []
    current_lines: list[str] = []
    current_start_line = 1
    current_length = 0

    def add_current_chunk(end_line: int) -> None:
        nonlocal current_lines, current_length

        content = "\n".join(current_lines)
        if content.strip():
            chunks.append(
                TextChunk(
                    content=content,
                    start_line=current_start_line,
                    end_line=end_line,
                )
            )
        current_lines = []
        current_length = 0

    for line_number, line in enumerate(lines, start=1):
        if len(line) > max_chars:
            if current_lines:
                add_current_chunk(line_number - 1)

            for start in range(0, len(line), max_chars):
                piece = line[start : start + max_chars]
                if piece.strip():
                    chunks.append(
                        TextChunk(
                            content=piece,
                            start_line=line_number,
                            end_line=line_number,
                        )
                    )
            current_start_line = line_number + 1
            continue

        separator_length = 1 if current_lines else 0
        if current_lines and current_length + separator_length + len(line) > max_chars:
            add_current_chunk(line_number - 1)
            current_start_line = line_number

        if not current_lines:
            current_start_line = line_number

        current_lines.append(line)
        current_length += separator_length + len(line)

    if current_lines:
        add_current_chunk(len(lines))

    return chunks
