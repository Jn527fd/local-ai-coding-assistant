import logging


def configure_logging(debug: bool = False) -> None:
    """Configure concise application logging when no handler exists yet."""

    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
