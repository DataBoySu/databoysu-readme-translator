# DataBoySu Readme Translator

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

 The action will automatically download the Aya model (see above) and commits README updates back to the repository by default. The action verifies token scopes at runtime and will fail if the provided token does not include the required `repo`/`public_repo` scope. Ensure your workflow grants `permissions: contents: write`.

Token configuration

- **Default secret name:** The action accepts an input `token_name` which is the name of the secret that contains a write-capable GitHub token. By default this is set to `GH_TOKEN` so you can provide a secret named `GH_TOKEN` (or use the built-in `GITHUB_TOKEN` by setting `token_name: 'GITHUB_TOKEN'`).
- **Custom secret:** If you store your token under a different secret name (for example `MY_WRITE_TOKEN`), set the input `token_name` to that name. The action will map `secrets[inputs.token_name]` to the internal `GITHUB_TOKEN` environment variable used by the script.

Example (use a custom secret named `MY_WRITE_TOKEN` stored in repository secrets):

```yaml
      - name: Translate README
        uses: DataBoySu/databoysu-readme-translator@v1
        with:
          lang: de
          nav_target: README.md
          token_name: MY_WRITE_TOKEN
```

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

