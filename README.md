# DataBoySu Readme Translator (databoysu-readme-translator)

DataBoySu's Readme Translator is a composite GitHub Action that translates a repository README and appends/updates a language navigation bar at the top of the README.

Features
- Translate README into a target language using a local GGUF model (via `llama-cpp-python`).
- Inject or update a navbar section delimited by `<!--START_SECTION:navbar-->` / `<!--END_SECTION:navbar-->`.
- Optional model download into the runner cache (`RUNNER_TOOL_CACHE`) when `model_url` is provided.
- Dry-run mode writes a preview file instead of modifying the README.

Quick start (example workflow)
1. Add this action to a workflow in your repository (example):

```yaml
uses: DataBoySu/databoysu-readme-translator@v1
with:
	lang: de
	model_path: /path/to/model.gguf
	nav_target: README.md
	dry_run: true
```

What repo owners must provide
- `GITHUB_TOKEN`: action uses the runner provided `${{ secrets.GITHUB_TOKEN }}`. The workflow must grant `contents: write` permission if you want the action to update the README (committing changes).
- A GGUF model path or model URL (optional): either mount a model into the runner, provide a `model_path`, or set `model_url` (the action will download into the runner cache).
- `lang` input: target language code (e.g., `de`, `fr`).

Local testing
1. Install dependencies locally:

```bash
python -m pip install -r readme-translator-action/requirements.txt
python -m pip install -r readme-translator-action/requirements-dev.txt
```

2. Dry-run translation on your README (doesn't modify README):

```bash
python readme-translator-action/translator/translate.py --lang de --model-path /path/to/model.gguf --dry-run
```

Running tests (pytest)

```bash
pip install -r readme-translator-action/requirements-dev.txt
pytest -q
```

Notes & caveats
- This is a first release; it uses `llama-cpp-python` and expects a GGUF model compatible with the runtime. Running the model on GitHub-hosted runners may be slow and storage-heavy. For more control over native dependencies consider packaging as a Docker action.
- The translator will create `locales/README.<lang>.md` in the action folder when run. The navbar links point to `locales/README.<lang>.md` relative to the README location.

Support & contribution
- License: MIT
- Author: DataBoySu

