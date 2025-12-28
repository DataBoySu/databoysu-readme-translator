# DataBoySu's Readme Translator

![GitHub Release](https://img.shields.io/github/v/release/DataBoySu/databoysu-readme-translator?style=for-the-badge&color=0366d6&logo=github)
![Build Status](https://img.shields.io/github/actions/workflow/status/DataBoySu/databoysu-readme-translator/ci.yml?style=for-the-badge&label=Build&logo=github-actions)
![Python Version](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python&logoColor=white)
![License](https://img.shields.io/badge/License-AGPL_3.0-purple?style=for-the-badge)

This Readme Translator is a composite GitHub Action that translates a repository README and appends/updates a language navigation bar at the top of the README.

This action runs entirely on the GitHub Runner, ensuring your data stays within the execution environment.

## Features

- Translate README into a target language using a local GGUF model (via `llama-cpp-python`).
- Inject or update a navbar section delimited by

```
 <!--START_SECTION:navbar--> 
 
 <!--END_SECTION:navbar-->
```

-- Automatic regeneration of the runner cache when missing.

## Translation Quality & Disclaimer

This action acts as a powerful **helper tool** designed to take your documentation **95% of the way** towards full localization. It utilizes a context-aware AI model optimized for technical content, ensuring that code blocks, HTML tags, and industry jargon are preserved.

While the quality is high, **manual review is required for the final 5%**. You may encounter occasional grammatical imperfections or untranslated segments if the model encounters ambiguous context. The repository owner is responsible for the final polish and verification of the translated content.

## Supported Languages

You can use any of the following codes in the `lang` input.

| Code | Language | | Code | Language | | Code | Language |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **fr** | French | | **de** | German | | **es** | Spanish |
| **ja** | Japanese | | **zh** | Chinese (Simplified) | | **ru** | Russian |
| **pt** | Portuguese | | **ko** | Korean | | **hi** | Hindi |
| **it** | Italian | | **nl** | Dutch | | **tr** | Turkish |
| **ar** | Arabic | | **vi** | Vietnamese | | **pl** | Polish |
| **uk** | Ukrainian | | **id** | Indonesian | | **cs** | Czech |
| **el** | Greek | | **he** | Hebrew | | **fa** | Persian |
| **ro** | Romanian | | **zh-tw**| Chinese (Traditional)| | | |

## Quick start (Drag & Drop)

To translate your README into the **9 default languages** automatically on push, or **manually specify languages** via the Actions tab, create a file named `.github/workflows/translate.yml` in your repository and paste the following:

```yaml
name: Translate Readme

on:
  workflow_dispatch:
    inputs:
      languages:
        description: 'Languages to translate (comma-separated)'
        required: false
        default: 'fr,de,es,ru'
  push:
    paths:
      - 'README.md'

permissions:
  contents: write

jobs:
  prepare:
    runs-on: ubuntu-latest
    outputs:
      matrix: ${{ steps.set-matrix.outputs.matrix }}
    steps:
      - id: set-matrix
        run: |
          if [ "${{ github.event_name }}" == "workflow_dispatch" ]; then
            LANGS="${{ github.event.inputs.languages }}"
          else
            LANGS="fr,de,es,ja,zh,ru,pt,ko,hi"
          fi
          # Create JSON array for matrix
          echo "matrix=$(echo $LANGS | jq -R -c 'split(",")')" >> $GITHUB_OUTPUT

  translate:
    needs: prepare
    runs-on: ubuntu-latest
    strategy:
      matrix:
        lang: ${{ fromJson(needs.prepare.outputs.matrix) }}
    steps:
      - uses: actions/checkout@v4

      - name: Run README Translator
      # @main is you want latest code, @v1 for stable yet outdated first release
        uses: DataBoySu/databoysu-readme-translator@v1
        with:
          lang: ${{ matrix.lang }}

      - name: Upload Translation
        uses: actions/upload-artifact@v4
        with:
          name: locale-${{ matrix.lang }}
          path: locales/README.${{ matrix.lang }}.md

  commit:
    needs: translate
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
          token: ${{ secrets.GH_TOKEN || secrets.GITHUB_TOKEN }}

      - name: Download Translations
        uses: actions/download-artifact@v4
        with:
          pattern: locale-*
          path: locales
          merge-multiple: true

      - name: Regenerate Navbar
        run: |
          python3 -c "
          import os, re
          readme_path = 'README.md'
          locales_dir = 'locales'
          nav_data = {
              "ar": ("🇸🇦", "العربية"), "cs": ("🇨🇿", "Čeština"), "de": ("🇩🇪", "Deutsch"),
              "el": ("🇬🇷", "Ελληνικά"), "en": ("🇺🇸", "English"), "es": ("🇪🇸", "Español"),
              "fa": ("🇮🇷", "فارسی"), "fr": ("🇫🇷", "Français"), "he": ("🇮🇱", "עברית"),
              "hi": ("🇮🇳", "हिंदी"), "id": ("🇮🇩", "Bahasa Indonesia"), "it": ("🇮🇹", "Italiano"),
              "ja": ("🇯🇵", "日本語"), "ko": ("🇰🇷", "한국어"), "nl": ("🇳🇱", "Nederlands"),
              "pl": ("🇵🇱", "Polski"), "pt": ("🇵🇹", "Português"), "ro": ("🇷🇴", "Română"),
              "ru": ("🇷🇺", "Русский"), "tr": ("🇹🇷", "Türkçe"), "uk": ("🇺🇦", "Українська"),
              "vi": ("🇻🇳", "Tiếng Việt"), "zh": ("🇨🇳", "中文"), "zh-tw": ("🇹🇼", "繁體中文")
          }
          if os.path.exists(locales_dir):
              langs = sorted([re.match(r'README\.(.+?)\.md$', f).group(1) for f in os.listdir(locales_dir) if re.match(r'README\.(.+?)\.md$', f)])
              links = [f'<a href="README.md">🇺🇸 English</a>']
              for l in langs:
                  flag, name = nav_data.get(l, ("🏳️", l.upper()))
                  links.append(f'<a href="locales/README.{l}.md">{flag} {name}</a>')
              navbar = ' | '.join(links)
              start, end = '<!--START_SECTION:navbar-->', '<!--END_SECTION:navbar-->'
              block = f'{start}\n<div align="center">\n  {navbar}\n</div>\n{end}\n\n'
              with open(readme_path, 'r', encoding='utf-8') as f: content = f.read()
              pattern = re.compile(f'{re.escape(start)}.*?{re.escape(end)}\s*', re.DOTALL)
              if pattern.search(content):
                  content = pattern.sub(block, content)
              else:
                  content = block + content
              with open(readme_path, 'w', encoding='utf-8') as f: f.write(content)
          "

      - name: Commit Translations
        uses: stefanzweifel/git-auto-commit-action@v5
        with:
          commit_message: "docs: update translations and navbar"
          file_pattern: 'README.md locales/*.md'
```

## Navigation Bar Behavior

The action automatically manages links between your translated files.

1. **Default**: If no navbar exists, one is **appended to the very top** of your `README.md`.
2. **Existing**: If a navbar exists, it updates the links based on the languages found in your `locales/` folder.
3. **Manual Placement**: If you want the navbar in a specific location (e.g., below a logo), add these markers to your `README.md`:

    ```markdown
    <!--START_SECTION:navbar-->
    <!--END_SECTION:navbar-->
    ```

## Inputs

| Input | Description | Required | Default |
| :--- | :--- | :--- | :--- |
| `lang` | Target language code (e.g., `fr`, `de`, `ja`) | **Yes** | N/A |
| `readme_path` | Path to the source README | No | `README.md` |
| `model_url` | Custom GGUF model URL | No | Aya Expanse 8B |

## Token & Permissions

By default, this workflow uses the automatic `GITHUB_TOKEN` to push changes back to your repository.

- **Permissions**: You must include `permissions: contents: write` in your workflow file.
- **Triggering Workflows**: The default `GITHUB_TOKEN` **cannot** trigger other workflows (like a GitHub Pages build). If you need this, create a Personal Access Token (PAT), add it as a secret named `GH_TOKEN`, and the workflow above will automatically use it.

## License

[AGPL-3.0](LICENSE)
