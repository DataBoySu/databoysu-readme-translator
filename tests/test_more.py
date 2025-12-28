import os
import sys

# Ensure package is importable when running pytest locally
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from readme_translator_action.translator.translate import (
    get_smart_chunks,
    merge_small_chunks,
    inject_navbar,
)


def test_merge_small_chunks_merges_header_and_paragraph():
    chunks = [('prose', '# Title'), ('prose', 'This is a paragraph that follows the title.')]
    merged = merge_small_chunks(chunks)
    # merged should contain combined content
    combined = ''.join([c for _, c in merged])
    assert '# Title' in combined and 'This is a paragraph' in combined


def test_merge_creates_hybrid_when_next_struct():
    chunks = [('prose', '# Header'), ('struct', '<div>foo</div>')]
    merged = merge_small_chunks(chunks)
    assert any(t == 'hybrid' for t, _ in merged)


def test_inject_navbar_appends_and_is_idempotent():
    readme = (
        "# Project\n\n"
        "<!--START_SECTION:navbar-->\n"
        "[fr](locales/README.fr.md)\n"
        "<!--END_SECTION:navbar-->\n\n"
        "Intro\n"
    )
    updated = inject_navbar(readme, ['de', 'fr'])
    assert '[fr](locales/README.fr.md)' in updated
    assert '[de](locales/README.de.md)' in updated

    # idempotent: running again should not duplicate
    updated2 = inject_navbar(updated, ['de', 'fr'])
    assert updated == updated2


def test_get_smart_chunks_detects_code_and_links():
    text = "Some text\n\n```py\nprint(1)\n```\n\n[link](http://example.com)\n"
    chunks = get_smart_chunks(text)
    types = [t for t, _ in chunks]
    assert 'struct' in types
