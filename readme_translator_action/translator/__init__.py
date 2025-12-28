"""Translator subpackage for readme_translator_action."""

from .translate import (
    get_smart_chunks,
    merge_small_chunks,
    inject_navbar,
    main,
)

__all__ = ["get_smart_chunks", "merge_small_chunks", "inject_navbar", "main"]
