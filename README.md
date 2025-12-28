# DataBoySu Readme Translator (databoysu-readme-translator)

DataBoySu's Readme Translator is a composite GitHub Action that translates a repository README and appends/updates a language navigation bar at the top of the README.

Features

- Translate README into a target language using a local GGUF model (via `llama-cpp-python`).
- Inject or update a navbar section delimited by `<!--START_SECTION:navbar-->` / `<!--END_SECTION:navbar-->`.
-- Automatic download of the Aya Expanse GGUF model into the runner cache when missing.

Quick start (example workflow)

1. Add this action to a workflow in your repository (example):

```yaml
uses: DataBoySu/databoysu-readme-translator@v1
with:
  lang: de
  nav_target: README.md
```

What repo owners must provide
- `GITHUB_TOKEN`: action uses the runner provided `${{ secrets.GITHUB_TOKEN }}`. The workflow must grant `contents: write` permission if you want the action to update the README (committing changes).
- Model download: the action automatically downloads the Aya Expanse GGUF model into the runner cache if none is present. No model inputs are required from repository owners. You can host a different model and update `entrypoint.sh`'s `DEFAULT_MODEL_URL` if desired.
- `lang` input: target language code (e.g., `de`, `fr`).

Committing changes from the Action

- The workflow must grant `contents: write` permission so the action can commit and push README updates. Add this at the top level of your workflow:

```yaml
permissions:
	contents: write
```

The action will automatically download the Aya model (see above) and commits README updates back to the repository by default. Ensure your workflow grants `contents: write` permission so the action can push changes.

Example workflow (commits by default):

```yaml
name: Translate README
on:
  workflow_dispatch:

permissions:
  contents: write

jobs:
  translate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Translate README
        uses: DataBoySu/databoysu-readme-translator@v1
        with:
          lang: de
          nav_target: README.md
```

Local testing
1. Install dependencies locally:

```bash
python -m pip install -r readme-translator-action/requirements.txt
```

2. Local translation (the action will download the Aya model automatically when run on a runner):

```bash
python -m readme_translator_action.translator.translate --lang de
```

Note: "dry run" previously referred to a mode that wrote a preview file (`readme_translator_preview.md`) instead of committing changes; in the marketplace action this behavior has been removed — the action always commits translated README updates back to the repository.

Running tests (pytest)

```bash
pip install -r readme-translator-action/requirements.txt
pytest -q
```

Notes & caveats

- This is a first release; it uses `llama-cpp-python` and expects a GGUF model compatible with the runtime. Running the model on GitHub-hosted runners may be slow and storage-heavy.

- The translator will create `locales/README.<lang>.md` in the action folder when run. The navbar links point to `locales/README.<lang>.md` relative to the README location.

Support & contribution
- License: [AGPL-3.0](LICENSE)
- Author: DataBoySu

