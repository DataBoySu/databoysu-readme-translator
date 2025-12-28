import os
import re
import argparse
from typing import List, Tuple

# Import llama inside main() to keep module import-safe for tests

LANG_MAP = {
    "de": "German", "fr": "French", "es": "Spanish", "ja": "Japanese",
    "zh": "Chinese(Simplified)", 
    "ru": "Russian", "pt": "Portuguese", "ko": "Korean", "hi": "Hindi",
    "ar": "Arabic", "cs": "Czech", "nl": "Dutch", "en": "English",
    "el": "Greek", "he": "Hebrew", "id": "Indonesian", "it": "Italian",
    "fa": "Persian", "pl": "Polish", "ro": "Romanian", "tr": "Turkish",
    "uk": "Ukrainian", "vi": "Vietnamese", "zh-tw": "Chinese(Traditional)",
}

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# language guidance (populated in main)
lang_guidance = ""


def get_system_header(target_lang_name: str) -> str:
    return (
        f"You are a technical translation filter for {target_lang_name}.\n"
        "STRICT RULES:\n"
        "- The input is a single section header. Translate it 1:1.\n"
        "- DO NOT generate any content, lists, or descriptions under the header.\n"
        "- Preserve the '#' symbols exactly.\n"
        "- Output ONLY the translated header.\n"
        "- Preserve original formatting, punctuation, whitespace, and markdown/code symbols exactly; do NOT normalize, reflow, or 'fix' the input."
    )


def get_system_prose(target_lang_name: str) -> str:
    return (
        f"You are a professional technical translation engine. Your task: Translate the input into {target_lang_name}.\n"
        "STRICT RULES:\n"
        "- Output ONLY the final translated text. No intros.\n"
        "- NEVER modify HTML tags, attributes (href, src), or CSS styles.\n"
        "- Keep technical terms (GPU, VRAM, CLI, Docker, GEMM, PIDs, NVLink) in English.\n"
        "- Preserve all Markdown symbols (#, **, `, -, [link](url)) exactly.\n"
        "- Do NOT modify formatting, whitespace, punctuation, code fences, list markers, or emphasis markers; translate only the human-visible text."
    )


def get_smart_chunks(text: str) -> List[Tuple[str, str]]:
    pattern = r'(' \
              r'```[\s\S]*?```|' \
              r'<div\b[^>]*>[\s\S]*?<\/div>|' \
              r'<details\b[^>]*>[\s\S]*?<\/details>|' \
              r'<section\b[^>]*>[\s\S]*?<\/section>|' \
              r'<table\b[^>]*>[\s\S]*?<\/table>|' \
              r'^#{1,6} .*' \
              r')'

    raw_parts = re.split(pattern, text, flags=re.MULTILINE | re.IGNORECASE)
    chunks = []

    for part in raw_parts:
        if not part or not part.strip():
            continue

        p = part.strip()

        # Treat blockquotes as prose
        if p.startswith('>'):
            chunks.append(("prose", p))
            continue

        if (
            p.startswith(('<div', '<details', '<section', '<table', '```')) or
            p.startswith('<!--') or p.endswith('-->') or
            re.match(r'!\[.*?\]\(.*?\)', p) or
            re.match(r'\[.*?\]\(.*?\)', p)
        ):
            chunks.append(("struct", p))
        else:
            chunks.append(("prose", p))

    # Post-process: split any `struct` chunk that contains blockquote lines into separate chunks
    new_chunks: List[Tuple[str, str]] = []
    for ctype, ctext in chunks:
        if ctype == 'struct' and re.search(r'^>\s', ctext, flags=re.MULTILINE):
            # split into segments where consecutive blockquote lines become their own parts
            parts = re.split(r'(^>.*(?:\n>.*)*)', ctext, flags=re.MULTILINE)
            for seg in parts:
                if not seg or not seg.strip():
                    continue
                s = seg.strip()
                if s.startswith('>'):
                    new_chunks.append(("prose", s))
                else:
                    new_chunks.append(("struct", s))
        else:
            new_chunks.append((ctype, ctext))

    return new_chunks


def merge_small_chunks(chunks: List[Tuple[str, str]], min_chars: int = 400) -> List[Tuple[str, str]]:
    merged = []
    i = 0
    while i < len(chunks):
        ctype, ctext = chunks[i]

        if ctype == "prose" and (ctext.startswith('#') or len(ctext) < 50) and i + 1 < len(chunks):
            next_ctype, next_ctext = chunks[i+1]
            combined_text = ctext + "\n\n" + next_ctext
            new_type = "hybrid" if next_ctype == "struct" else "prose"
            merged.append((new_type, combined_text))
            i += 2 
        else:
            merged.append((ctype, ctext))
            i += 1
    return merged


def translate_chunk(text: str, llm_callable, is_lone_header: bool = False) -> str:
    # llm_callable is expected to be a callable that returns a dict with ['choices'][0]['text']
    target = llm_callable.target_lang_name if hasattr(llm_callable, 'target_lang_name') else ''
    current_system_prompt = get_system_header(target) if is_lone_header else get_system_prose(target)
    global lang_guidance
    if lang_guidance and not is_lone_header:
        current_system_prompt = f"{get_system_prose(target)}\n\nADDITIONAL GUIDANCE:\n{lang_guidance}"

    prompt = f"""<|START_OF_TURN_TOKEN|><|SYSTEM_TOKEN|>\n{current_system_prompt}\n<|END_OF_TURN_TOKEN|>\n<|START_OF_TURN_TOKEN|><|USER_TOKEN|>\n{text}<|END_OF_TURN_TOKEN|>\n<|START_OF_TURN_TOKEN|><|CHATBOT_TOKEN|>"""

    response = llm_callable(prompt, max_tokens=8192, temperature=0, stop=["<|END_OF_TURN_TOKEN|>"])
    translated = response['choices'][0]['text'].strip()

    if translated.startswith("```"):
        lines = translated.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        translated = "\n".join(lines).strip()

    return translated


def inject_navbar(readme_text: str, langs: List[str]) -> str:
    start_marker = '<!--START_SECTION:navbar-->'
    end_marker = '<!--END_SECTION:navbar-->'

    def make_link(l):
        href = f'locales/README.{l}.md'
        return f'[{l}]({href})'

    # If navbar exists, parse existing links and add any missing langs
    if start_marker in readme_text and end_marker in readme_text:
        before, rest = readme_text.split(start_marker, 1)
        body, after = rest.split(end_marker, 1)

        existing = re.findall(r'\[([^\]]+)\]\([^\)]+\)', body)
        ordered = [make_link(x) for x in existing]
        for l in langs:
            if l not in existing:
                ordered.append(make_link(l))

        navbar = ' | '.join(ordered)
        # Replace existing navbar content without adding extra blank lines
        block = f"{start_marker}\n{navbar}\n{end_marker}"
        return before + block + after

    new_links = [make_link(l) for l in langs]
    navbar = ' | '.join(new_links)
    block = f"{start_marker}\n{navbar}\n{end_marker}\n\n"
    return block + readme_text


def main(lang: str, model_path: str = '', nav_target: str = 'README.md', dry_run: bool = False):
    """Run translation for a single language.

    This function performs LLM initialization lazily and is safe to import in tests.
    """
    global lang_guidance
    target_lang_name = LANG_MAP.get(lang, "English")

    scripts_dir = os.path.join(BASE_DIR, "scripts")
    guidance_file = os.path.join(scripts_dir, f"{lang}.txt")
    lang_guidance = ""
    if os.path.exists(guidance_file):
        with open(guidance_file, 'r', encoding='utf-8') as f:
            lang_guidance = f.read().strip()

    readme_path = os.path.join(BASE_DIR, nav_target)
    output_dir = os.path.join(BASE_DIR, 'locales')
    output_path = os.path.join(output_dir, f'README.{lang}.md')

    # Initialize LLM here to avoid import-time side-effects
    try:
        from llama_cpp import Llama
    except Exception as e:
        raise RuntimeError("llama-cpp-python is required to run translations") from e

    mp = model_path or os.path.join(BASE_DIR, 'models', 'aya-expanse-8b-Q4_K_M.gguf')
    llm = Llama(model_path=mp, n_ctx=8192, n_threads=2, verbose=False)

    # attach a small attribute used by translate_chunk for target name (best-effort)
    try:
        llm.target_lang_name = target_lang_name
    except Exception:
        pass

    os.makedirs(output_dir, exist_ok=True)

    with open(readme_path, 'r', encoding='utf-8') as f:
        content = f.read()

    chunks = merge_small_chunks(get_smart_chunks(content))

    final_output = []
    multiplier = 2.5

    for i, (ctype, ctext) in enumerate(chunks):
        if ctype == 'struct':
            final_output.append(ctext + '\n\n')
            continue

        is_lone_header = ctext.strip().startswith('#') and '\n' not in ctext.strip()
        translated = translate_chunk(ctext, llm, is_lone_header)

        if len(translated) > multiplier * len(ctext):
            translated = ctext

        final_output.append(translated.rstrip() + '\n\n')

    full_text = ''.join(final_output)

    full_text = re.sub(r'(\[.*?\]\()(?!(?:http|/|#|\.\./))', r'\1../', full_text)
    full_text = re.sub(r'((?:src|href)=["\"])(?!(?:http|/|#|\.\./))', r'\1../', full_text)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(full_text)

    locales_dir = os.path.join(BASE_DIR, 'locales')
    discovered = []
    if os.path.isdir(locales_dir):
        for fname in os.listdir(locales_dir):
            m = re.match(r'README\.(.+?)\.md$', fname)
            if m:
                discovered.append(m.group(1))

    if lang not in discovered:
        discovered.append(lang)

    locales = sorted(discovered)

    with open(readme_path, 'r', encoding='utf-8') as f:
        original = f.read()

    updated = inject_navbar(original, locales)

    if dry_run:
        out_preview = os.path.join(BASE_DIR, 'readme_translator_preview.md')
        with open(out_preview, 'w', encoding='utf-8') as f:
            f.write(updated)
        print(f'[DRY RUN] Wrote preview to {out_preview}')
    else:
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(updated)
        print(f'[SUCCESS] Wrote translated locales to {output_path} and injected navbar into {readme_path}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--lang", type=str, required=True)
    parser.add_argument("--model-path", type=str, default="")
    parser.add_argument("--nav-target", type=str, default="README.md")
    parser.add_argument("--dry-run", action='store_true')
    args = parser.parse_args()

    main(args.lang, model_path=args.model_path, nav_target=args.nav_target, dry_run=args.dry_run)
