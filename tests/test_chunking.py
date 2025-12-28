import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from readme_translator_action.translator.translate import get_smart_chunks, merge_small_chunks


def test_get_smart_chunks_blockquote():
    text = "<!-- HTML_BLOCK -->\n\n> *MyGPU: Lightweight GPU Management Utility*\n\n<!-- HTML_BLOCK -->"
    chunks = get_smart_chunks(text)
    # Expect at least one struct for the HTML and one prose for the blockquote
    types = [t for t, _ in chunks]
    assert 'prose' in types


def test_merge_small_chunks():
    chunks = [('prose', '# Header'), ('struct', '<div>foo</div>')]
    merged = merge_small_chunks(chunks)
    assert any(t in ('prose', 'hybrid') for t, _ in merged)
