from sample_app.calculator import add, multiply


def build_summary(first: int, second: int) -> str:
    """Return a readable summary of two basic calculations."""

    total = add(first, second)
    product = multiply(first, second)
    return f"sum={total}, product={product}"


if __name__ == "__main__":
    print(build_summary(3, 4))
