from app.ai.output_sanitizer import ReasoningStreamFilter, strip_reasoning_text


def test_strip_reasoning_text_removes_think_blocks() -> None:
    assert (
        strip_reasoning_text("<think>private reasoning</think>\nFinal answer.")
        == "Final answer."
    )


def test_strip_reasoning_text_removes_unclosed_think_block() -> None:
    assert strip_reasoning_text("Visible\n<think>unfinished") == "Visible"


def test_reasoning_stream_filter_hides_split_think_blocks() -> None:
    stream_filter = ReasoningStreamFilter()

    visible = [
        stream_filter.feed("Hel"),
        stream_filter.feed("lo <thi"),
        stream_filter.feed("nk>private"),
        stream_filter.feed(" reasoning</thi"),
        stream_filter.feed("nk> world"),
        stream_filter.flush(),
    ]

    assert "".join(visible) == "Hello  world"
