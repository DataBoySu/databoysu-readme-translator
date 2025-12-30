<div align="center">

<h1>
<picture>
<img src="assets/alt_banner.gif">
</picture>
</h1>

![GitHub Release](https://img.shields.io/github/v/release/DataBoySu/databoysu-readme-translator?style=for-the-badge&color=0366d6&logo=github)
![Build Status](https://img.shields.io/github/actions/workflow/status/DataBoySu/databoysu-readme-translator/ci.yml?style=for-the-badge&label=Build&logo=github-actions)
![Python Version](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python&logoColor=white)
![License](https://img.shields.io/badge/License-AGPL_3.0-purple?style=for-the-badge)
[![If You Liked!](https://img.shields.io/static/v1?label=%E2%AD%90&message=If%20You%20Liked!&style=for-the-badge&color=BC4E99)](https://github.com/DataBoySu/databoysu-readme-translator)

</div>

This Readme Translator is a composite GitHub Action that translates a repository README and injects a language navigation bar at the top of the README.

This action runs entirely on the GitHub Runner, ensuring 100% Privacy focused and deterministic translation.

## Features

- Translate README into a target language using a local GGUF model (via `llama-cpp-python`).
- Injects and updates a navbar section in your REDADME delimited by

```
 <!--START_SECTION:navbar--> 
 
 <!--END_SECTION:navbar-->
```

- Uses multi-step validation approach to prevent format breaks, hallucinations, etc.
- Supports 20+ languages.
- Automatic caching of the model weights and parallel execution of translation jobs for sped up translations.

---

> [!IMPORTANT]
> This translation tool is primarily meant for **public repositories** \
> It relies on the public instances of GitHub Action Runners to run
>
> While private repo owners can also run this pipeline, they should be aware that \
> an average language translation job takes 40 minutes to run
>
> So it is recommended for everyone to use the example workflow given below \
> to parallely spin up multiple jobs and translate everything in one go

---

## Translation Quality & Disclaimer

This action acts as a pretty powerful **helper tool** designed to take your documentation **90-95% of the way** towards full localization.

It utilizes a context-aware AI model structurally optimized for technical content, ensuring that code blocks, tags, and jargon is preserved.

As a fail-safe, I have implemented complex post-processing which reverts document chunk back to original language(English) if it detects my set rule violations.

While the quality is high, **manual review is required for the final 5%**.

> [!NOTE] 
> This pipeline was **not made to replace human documentation localizers** \
> but to provide them a **ready-made template** \
> to style & improve the tone and wordings as they prefer, instead of having to make such translations from scratch.

From Beginners starting out GitHub to experienced maintainers looking to create new projects, and want to whip up a quick multi-lingual readme can use this tool for one-click setup without any hassle.



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
        default: 'fr,de,es,ja,zh,ru,pt,ko,hi'
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
      # Use @latest for the most up-to-date release, or @main for the bleeding edge
        uses: DataBoySu/databoysu-readme-translator@latest
        with:
          lang: ${{ matrix.lang }}

      - name: Uploading Translation Artifacts
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
          ref: ${{ github.head_ref || github.ref_name }}
          token: ${{ secrets.GH_TOKEN || secrets.GITHUB_TOKEN }}

      - name: Pull latest changes
        run: git pull origin ${{ github.head_ref || github.ref_name }} --rebase

      - name: Download Translations
        uses: actions/download-artifact@v4
        with:
          pattern: locale-*
          path: locales
          merge-multiple: true

      - name: Navigation Bar
        uses: DataBoySu/databoysu-readme-translator@latest
        with:
          mode: navbar

      - name: Commit Changes
        uses: stefanzweifel/git-auto-commit-action@v5
        with:
          commit_message: "✨💖 docs: updated translations & navbar! 🌸✨"
          # To use your own avatar, uncomment and set your name/email:
          # commit_author: "Your Name <your-email@example.com>"
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
