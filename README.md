# DataBoySu Readme Translator

DataBoySu's Readme Translator is a composite GitHub Action that translates a repository README and appends/updates a language navigation bar at the top of the README. This action runs entirely on the GitHub Runner, ensuring your data stays within the execution environment.

## Features

- Translate README into a target language using a local GGUF model (via `llama-cpp-python`).
- Inject or update a navbar section delimited by `<!--START_SECTION:navbar-->` / `<!--END_SECTION:navbar-->`.
-- Automatic download of the Aya Expanse GGUF model into the runner cache when missing.

## Quick start (Drag & Drop)

To translate your README into the **9 default languages** (French, German, Spanish, Japanese, Chinese, Russian, Portuguese, Korean, Hindi), create a file named `.github/workflows/translate.yml` in your repository and paste the following:

```yaml
name: Translate Readme

on:
  push:
    paths:
      - 'README.md'

permissions:
  contents: write

jobs:
  translate:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        # The 9 default languages
        lang: [fr, de, es, ja, zh, ru, pt, ko, hi]
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Run README Translator
        uses: DataBoySu/databoysu-readme-translator@main
        with:
          lang: ${{ matrix.lang }}

      - name: Commit Translations
        uses: stefanzweifel/git-auto-commit-action@v5
        with:
          commit_message: "docs: update README.${{ matrix.lang }}.md and navbar"
          file_pattern: 'README.md locales/*.md'
```

## Navigation Bar Behavior

The action automatically manages links between your translated files.

1.  **Default**: If no navbar exists, one is **appended to the very top** of your `README.md`.
2.  **Existing**: If a navbar exists, it updates the links based on the languages found in your `locales/` folder.
3.  **Manual Placement**: If you want the navbar in a specific location (e.g., below a logo), add these markers to your `README.md`:

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

- **Permissions**: You must include `permissions: contents: write` in your workflow file (as shown above).
- **Custom Token**: If you need the translation commit to trigger *other* workflows (e.g., a GitHub Pages build), you must use a Personal Access Token (PAT) instead of the default `GITHUB_TOKEN`. Configure it in the `actions/checkout` step and the `git-auto-commit-action`.

## License

[AGPL-3.0](LICENSE)
