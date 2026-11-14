"""citecheck: check whether an AI answer is supported by the sources it cites."""
from .core import Result, check_answer, split_claims, summarize

__all__ = ["Result", "check_answer", "split_claims", "summarize"]
