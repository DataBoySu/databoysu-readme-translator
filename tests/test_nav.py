from readme_translator_action.translator.translate import inject_navbar


def test_inject_navbar_creates_section():
    readme = "# Project\n\nSome intro.\n"
    updated = inject_navbar(readme, ['de', 'fr'])
    assert '<!--START_SECTION:navbar-->' in updated
    assert '[de](locales/README.de.md)' in updated
