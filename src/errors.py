"""Exceptions raised by the recommender.

Having a project-specific exception type lets the CLI catch the failures it
knows how to explain and turn them into a readable message, while genuinely
unexpected bugs still surface as normal tracebacks.
"""


class RecommenderError(Exception):
    """Base class for every error this project raises deliberately."""


class CatalogError(RecommenderError):
    """The song catalog could not be read or contained no usable rows."""
