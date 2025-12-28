"""
Translation module for the README translator action.
Handles chunking, translation via LLM, and navbar injection.
"""
import os
import re
import argparse

# translation pipeline for GitHub Action

LANG_MAP = {
    "de": "German", "fr": "French", "es": "Spanish", "ja": "Japanese",
    "zh": "Chinese(Simplified)", 
    "ru": "Russian", "pt": "Portuguese", "ko": "Korean", "hi": "Hindi",
    "ar": "Arabic", "cs": "Czech", "nl": "Dutch", "en": "English",
    "el": "Greek", "he": "Hebrew", "id": "Indonesian", "it": "Italian",
    "fa": "Persian", "pl": "Polish", "ro": "Romanian", "tr": "Turkish",
    "uk": "Ukrainian", "vi": "Vietnamese", "zh-tw": "Chinese(Traditional)",
}

NAV_DATA = {
    "ar": ("🇸🇦", "العربية"),
    "cs": ("🇨🇿", "Čeština"),
    "de": ("🇩🇪", "Deutsch"),
    "el": ("🇬🇷", "Ελληνικά"),
    "en": ("🇺🇸", "English"),
    "es": ("🇪🇸", "Español"),
    "fa": ("🇮🇷", "فارسی"),
    "fr": ("🇫🇷", "Français"),
    "he": ("🇮🇱", "עברית"),
    "hi": ("🇮🇳", "हिंदी"),
    "id": ("🇮🇩", "Bahasa Indonesia"),
    "it": ("🇮🇹", "Italiano"),
    "ja": ("🇯🇵", "日本語"),
    "ko": ("🇰🇷", "한국어"),
    "nl": ("🇳🇱", "Nederlands"),
    "pl": ("🇵🇱", "Polski"),
    "pt": ("🇵🇹", "Português"),
    "ro": ("🇷🇴", "Română"),
    "ru": ("🇷🇺", "Русский"),
    "tr": ("🇹🇷", "Türkçe"),
    "uk": ("🇺🇦", "Українська"),
    "vi": ("🇻🇳", "Tiếng Việt"),
    "zh": ("🇨🇳", "中文"),
    "zh-tw": ("🇹🇼", "繁體中文"),
}

# Forbidden phrases that indicate hallucination
FORBIDDEN = [
    # English
    "This section", "In this", "In this section", "means", "explains",
    # Chinese (Simplified)
    "以下", "说明", "本节", "在这里", "意味着", "解释",
    # German
    "Dieser Abschnitt", "In diesem", "In diesem Abschnitt", "bedeutet", "erklärt",
    # French
    "Cette section", "Dans cette", "Dans cette section", "signifie", "explique",
    # Spanish
    "Esta sección", "En esta", "En esta sección", "significa", "explica",
    # Japanese
    "このセクション", "この中で", "このセクションでは", "意味する", "説明する",
    # Russian
    "Этот раздел", "В этом", "В этом разделе", "означает", "объясняет", "ниже",
    # Arabic
    "هذا القسم", "في هذا", "في هذا القسم", "يعني", "يشرح",
    # Czech
    "Tato sekce", "V tomto", "V této sekci", "znamená", "vysvětluje",
    # Dutch
    "Deze sectie", "In dit", "In deze sectie", "betekent", "verklaart",
    # Greek
    "Αυτό το τμήμα", "Σε αυτό", "Σε αυτό το τμήμα", "σημαίνει", "εξηγεί",
    # Hebrew
    "סעיף זה", "בזה", "בסעיף זה", "משמעותו", "מסביר",
    # Indonesian
    "Bagian ini", "Dalam ini", "Di bagian ini", "berarti", "menjelaskan",
    # Italian
    "Questa sezione", "In questo", "In questa sezione", "significa", "spiega",
    # Persian (Farsi)
    "این بخش", "در این", "در این بخش", "معنی می‌دهد", "توضیح می‌دهد",
    # Polish
    "Ta sekcja", "W tym", "W tej sekcji", "oznacza", "wyjaśnia",
    # Romanian
    "Această secțiune", "În acest", "În această secțiune", "înseamnă", "explică",
    # Turkish
    "Bu bölüm", "Bunda", "Bu bölümde", "anlamına gelir", "açıklar",
    # Ukrainian
    "Цей розділ", "У цьому", "У цьому розділі", "означає", "пояснює",
    # Vietnamese
    "Phần này", "Trong này", "Trong phần này", "có nghĩa là", "giải thích",
    # Traditional Chinese
    "以下", "說明", "本節", "在這裡", "意味著", "解釋",
    # Portuguese
    "Esta seção", "Nesta seção", "significa", "explica",
    # Korean
    "이 섹션", "이 안에서", "이 섹션에서는", "의미한다", "설명한다",
    # Hindi
    "यह अनुभाग", "इसमें", "इस अनुभाग में", "का अर्थ है", "समझाता है",
]

# Language-specific expansion multipliers for length validation
HIGH_MULTIPLIER_MAP = {
    "ja": 5.5,  # Japanese can expand significantly
    "hi": 5.5,  # Hindi often requires more tokens
    "ar": 4.0,  # Arabic expands moderately
    "he": 4.0,  # Hebrew
    "fa": 4.0,  # Persian (Farsi)
    "ru": 3.5,  # Russian
    "uk": 3.5,  # Ukrainian
    "pl": 3.5,  # Polish
}

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 2. Smart Chunking Functions

def _classify_text_as_struct_or_prose(text):
    """Classify text chunk as structure (HTML/comments) or prose."""
    t = text.strip()
    if (
        t.startswith(('<div', '<details', '```')) or
        t.startswith('<!--') or t.endswith('-->') or
        # Strict check: Chunk must be ONLY images/links (no prose text)
        re.fullmatch(r'(?:\s*(?:!\[.*?\]\(.*?\)|\[.*?\]\(.*?\))\s*)+', t, flags=re.DOTALL)
    ):
        return 'struct'
    return 'prose'


def split_struct_blockquotes(chunks):
    """Split any `struct` chunk that contains a markdown blockquote into
    a `struct` part before the quote, a `prose` blockquote part, and an
    optional tail (struct/prose) after. This handles cases where placeholders
    like <!-- HTML_BLOCK --> are adjacent to a quoted one-line description.
    """
    out = []
    for ctype, ctext in chunks:
        if ctype != 'struct' or not re.search(r'^\s*>', ctext, flags=re.MULTILINE):
            out.append((ctype, ctext))
            continue

        # Work with original lines to preserve spacing
        lines = ctext.splitlines(True)

        # find first line that starts with '>' (block quote)
        start = None
        for idx, line in enumerate(lines):
            if line.lstrip().startswith('>'):
                start = idx
                break

        if start is None:
            out.append((ctype, ctext))
            continue

        # find end of contiguous blockquote region, include adjacent blank lines
        end = start
        while end + 1 < len(lines):
            nxt = lines[end + 1]
            if nxt.lstrip().startswith('>'):
                end += 1
                continue
            # include a single blank line immediately after blockquote
            if nxt.strip() == '':
                # only include if followed by another blockquote line
                if end + 2 < len(lines) and lines[end + 2].lstrip().startswith('>'):
                    end += 1
                    continue
                # otherwise, treat blank as separator and stop
                break
            break

        before = ''.join(lines[:start]).strip()
        block = ''.join(lines[start:end+1]).strip()
        after = ''.join(lines[end+1:]).strip()

        if before:
            out.append(('struct', before))
        out.append(('prose', block))
        if after:
            out.append((_classify_text_as_struct_or_prose(after), after))

    return out

def get_smart_chunks(text):
    """Split text into smart chunks based on markdown/html patterns."""
    pattern = r'(' \
              r'```[\s\S]*?```|' \
              r'<div\b[^>]*>[\s\S]*?<\/div>|' \
              r'<details\b[^>]*>[\s\S]*?<\/details>|' \
              r'<section\b[^>]*>[\s\S]*?<\/section>|' \
              r'<table\b[^>]*>[\s\S]*?<\/table>|' \
              r'^\s*(?:[!\[].*?\]\(.*?\)\s*)+$|' \
              r'^#{1,6} .*' \
              r')'

    raw_parts = re.split(pattern, text, flags=re.MULTILINE | re.IGNORECASE)
    chunks = []

    for part in raw_parts:
        if not part or not part.strip():
            continue
        
        stripped_part = part.strip()

        # Treat blockquotes as prose
        if stripped_part.startswith('>'):
            chunks.append(("prose", stripped_part))
            continue

        if (
            stripped_part.startswith(('<div', '<details', '<section', '<table', '```')) or
            stripped_part.startswith('<!--') or stripped_part.endswith('-->') or
            re.match(r'!\[.*?\]\(.*?\)', stripped_part) or
            re.match(r'\[.*?\]\(.*?\)', stripped_part)
        ):
            chunks.append(("struct", stripped_part))
        else:
            chunks.append(("prose", stripped_part))

    return chunks


def merge_small_chunks(chunks, min_chars=50):
    """Merge small prose chunks to prevent fragmentation."""
    merged = []
    i = 0
    while i < len(chunks):
        ctype, ctext = chunks[i]

        # Check if chunk is too small or is a header, and merge with next if possible
        is_small = len(ctext) < min_chars
        if ctype == "prose" and (ctext.startswith('#') or is_small) and i + 1 < len(chunks):
            next_ctype, next_ctext = chunks[i+1]
            combined_text = ctext + "\n\n" + next_ctext
            new_type = "hybrid" if next_ctype == "struct" else "prose"
            merged.append((new_type, combined_text))
            i += 2
        else:
            merged.append((ctype, ctext))
            i += 1
    return merged


# 3. Prompts
def translate_chunk(text, llm, prompts, lang_guidance=None, is_lone_header=False):
    """Translate a single chunk using llama-cpp-python."""
    current_system_prompt = prompts['header'] if is_lone_header else prompts['prose']
    if lang_guidance and not is_lone_header:
        current_system_prompt = f"{prompts['prose']}\n\nADDITIONAL GUIDANCE:\n{lang_guidance}"

    prompt = (
        f"<|START_OF_TURN_TOKEN|><|SYSTEM_TOKEN|>\n{current_system_prompt}\n<|END_OF_TURN_TOKEN|>\n"
        f"<|START_OF_TURN_TOKEN|><|USER_TOKEN|>\n{text}<|END_OF_TURN_TOKEN|>\n"
        "<|START_OF_TURN_TOKEN|><|CHATBOT_TOKEN|>"
    )

    # Dynamic max_tokens to prevent infinite loops on small inputs
    # Estimate: 3 tokens per char upper bound, min 256, max 4096
    estimated_limit = int(len(text) * 3) + 200
    gen_limit = min(4096, max(256, estimated_limit))

    response = llm(prompt, max_tokens=gen_limit, temperature=0, stop=["<|END_OF_TURN_TOKEN|>"])
    translated = response['choices'][0]['text'].strip()

    if translated.startswith("```"):
        lines = translated.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        translated = "\n".join(lines).strip()

    return translated


def inject_navbar(readme_text, langs):
    """Inject or update the navigation bar in the README."""
    start_marker = '<!--START_SECTION:navbar-->'
    end_marker = '<!--END_SECTION:navbar-->'

    links = []
    # Always include English (Root) first
    flag, name = NAV_DATA.get("en", ("🇺🇸", "English"))
    links.append(f'<a href="README.md">{flag} {name}</a>')

    for l in sorted(langs):
        if l == "en": continue
        if l in NAV_DATA:
            flag, name = NAV_DATA[l]
        else:
            flag, name = "🏳️", l.upper()
        href = f"locales/README.{l}.md"
        links.append(f'<a href="{href}">{flag} {name}</a>')

    navbar_content = ' | '.join(links)
    html_block = f'<div align="center">\n  {navbar_content}\n</div>'
    block = f"{start_marker}\n{html_block}\n{end_marker}\n\n"

    # Regex to replace existing block (handling potential multiline content between markers)
    pattern = re.compile(f'{re.escape(start_marker)}.*?{re.escape(end_marker)}\s*', re.DOTALL)

    if pattern.search(readme_text):
        return pattern.sub(block, readme_text)
    else:
        return block + readme_text


def get_system_prompts(target_lang_name):
    """Generate system prompts for the target language."""
    header = (
        f"You are a technical translation filter for {target_lang_name}.\n"
        "STRICT RULES:\n"
        "- The input is a single section header. Translate it 1:1.\n"
        "- DO NOT generate any content, lists, or descriptions under the header.\n"
        "- Preserve the '#' symbols exactly.\n"
        "- Output ONLY the translated header.\n"
        "- Preserve original formatting, punctuation, whitespace, and markdown/code symbols exactly;"
        " do NOT normalize, reflow, or 'fix' the input."
    )

    prose = (
        f"You are a professional technical translation engine. "
        f"Your task: Translate the input into {target_lang_name}.\n"
        "STRICT RULES:\n"
        "- Output ONLY the final translated text. No intros.\n"
        "- NEVER modify HTML tags, attributes (href, src), or CSS styles.\n"
        "- Keep technical terms in English.\n"
        "- Preserve all Markdown symbols (#, **, `, -, link) exactly.\n"
        "- Do NOT translate GitHub Flavored Markdown alerts (e.g., '> [!NOTE]', '> [!IMPORTANT]').\n"
        "- Do NOT translate badge/shield alt text or URLs.\n"
        "- Do NOT modify formatting, whitespace, punctuation, code fences, list markers, "
        "or emphasis markers; translate only the human-visible text.\n"
        "- Markdown Admonitions: NEVER translate the keyword inside > [!KEYWORD]. Valid keywords are: NOTE, TIP, IMPORTANT, WARNING, CAUTION.\n"
        "- Static Badges: Do not translate text inside image URLs (e.g., img.shields.io) unless it is the alt text.\n"
        "- Emoji Integrity: Ensure emojis remain attached to their correct logical counterparts."

    )
    return header, prose


def load_guidance(lang):
    """Load language-specific guidance from scripts directory."""
    scripts_dir = os.path.join(BASE_DIR, "scripts")
    guidance_file = os.path.join(scripts_dir, f"{lang}.txt")
    if os.path.exists(guidance_file):
        with open(guidance_file, "r", encoding="utf-8") as f:
            return f.read().strip()
    return ""


def process_chunks(chunks, llm, lang, prompts, lang_guidance):
    """Translate chunks and return joined text."""
    final_output = []
    multiplier = HIGH_MULTIPLIER_MAP.get(lang, 2.5)

    total_chunks = len(chunks)
    print(f"[INFO] Processing {total_chunks} chunks for language '{lang}'...", flush=True)

    for i, (ctype, ctext) in enumerate(chunks):
        if ctype == 'struct':
            final_output.append(ctext + '\n\n')
            continue

        print(f"[INFO] Translating chunk {i+1}/{total_chunks} ({len(ctext)} chars)...", flush=True)
        is_lone_header = ctext.strip().startswith('#') and '\n' not in ctext.strip()
        translated = translate_chunk(
            ctext, llm, prompts, lang_guidance, is_lone_header
        )

        if len(translated) > multiplier * len(ctext) or any(f in translated for f in FORBIDDEN):
            print(f"[WARN] Chunk {i+1} failed validation, using original text", flush=True)
            translated = ctext

        final_output.append(translated.rstrip() + '\n\n')

    return ''.join(final_output)


def run_translation_pipeline(content, llm, lang, prompts, lang_guidance):
    """Execute the chunking and translation steps."""
    chunks = get_smart_chunks(content)
    chunks = split_struct_blockquotes(chunks)
    chunks = merge_small_chunks(chunks)

    full_text = process_chunks(chunks, llm, lang, prompts, lang_guidance)
    
    # Post-processing: Fix relative paths
    full_text = re.sub(r'(\[.*?\]\()(?!(?:http|/|#|\.\./))', r'\1../', full_text)
    full_text = re.sub(r'((?:src|href)=["\'])(?!(?:http|/|#|\.\./))', r'\1../', full_text)
    
    return full_text


def regenerate_all_navbars(readme_path, locales_dir):
    """Regenerate navbars for the root README and all locale files."""
    if not os.path.exists(locales_dir):
        print(f"[INFO] No locales directory found at {locales_dir}. Skipping navbar generation.")
        return

    # Discover languages
    langs = []
    for f in os.listdir(locales_dir):
        match = re.match(r'README\.(.+?)\.md$', f)
        if match and match.group(1) in NAV_DATA:
            langs.append(match.group(1))
    langs.sort()
    
    # Helper to generate HTML
    def get_nav_html(is_root):
        links = []
        # English (Root)
        en_flag, en_name = NAV_DATA.get('en', ('🇺🇸', 'English'))
        en_href = 'README.md' if is_root else '../README.md'
        links.append(f'<a href="{en_href}">{en_flag} {en_name}</a>')
        
        for l in langs:
            flag, name = NAV_DATA.get(l, ('🏳️', l.upper()))
            href = f'locales/README.{l}.md' if is_root else f'README.{l}.md'
            links.append(f'<a href="{href}">{flag} {name}</a>')
        
        return ' | '.join(links)

    # Helper to update file
    def update_file(path, block):
        if not os.path.exists(path): return
        with open(path, 'r', encoding='utf-8') as f: content = f.read()
        start, end = '<!--START_SECTION:navbar-->', '<!--END_SECTION:navbar-->'
        # Regex to replace existing block
        pattern = re.compile(f'{re.escape(start)}.*?{re.escape(end)}\s*', re.DOTALL)
        if pattern.search(content):
            content = pattern.sub(block, content)
        else:
            content = block + content
        with open(path, 'w', encoding='utf-8') as f: f.write(content)

    # 1. Update Root
    root_nav = get_nav_html(is_root=True)
    start, end = '<!--START_SECTION:navbar-->', '<!--END_SECTION:navbar-->'
    root_block = f'{start}\n<div align="center">\n  {root_nav}\n</div>\n{end}\n\n'
    update_file(readme_path, root_block)

    # 2. Update Locales
    locale_nav = get_nav_html(is_root=False)
    locale_block = f'{start}\n<div align="center">\n  {locale_nav}\n</div>\n{end}\n\n'
    for l in langs:
        update_file(os.path.join(locales_dir, f'README.{l}.md'), locale_block)
    
    print(f"[SUCCESS] Regenerated navbars for Root and {len(langs)} locales.")


def update_navbar_in_readme(readme_path, output_dir, lang):
    """Discover locales and update the README navbar."""
    locales_dir = output_dir
    discovered = []
    if os.path.isdir(locales_dir):
        for fname in os.listdir(locales_dir):
            m = re.match(r'README\.(.+?)\.md$', fname)
            if m:
                discovered.append(m.group(1))

    # Ensure current language is present
    if lang not in discovered:
        discovered.append(lang)

    # sort for deterministic order, but keep existing order if present
    # we'll sort to keep behavior predictable
    locales = sorted(discovered)

    with open(readme_path, 'r', encoding='utf-8') as f:
        original = f.read()

    updated = inject_navbar(original, locales)

    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(updated)


def main(lang, model_path='', nav_target='README.md', mode='translate'):
    """Run translation for a single language.

    Parameters:
    - lang: language code
    - model_path: path to GGUF model file
    - nav_target: README path relative to repo root
    - mode: 'translate' or 'navbar'
    """
    # Use current working directory for target repo files
    readme_path = os.path.abspath(nav_target)
    output_dir = os.path.join(os.getcwd(), "locales")

    if mode == 'navbar':
        regenerate_all_navbars(readme_path, output_dir)
        return

    target_lang_name = LANG_MAP.get(lang, "English")

    header_prompt, prose_prompt = get_system_prompts(target_lang_name)
    prompts = {'header': header_prompt, 'prose': prose_prompt}
    lang_guidance = load_guidance(lang)

    output_path = os.path.join(output_dir, f"README.{lang}.md")

    # Initialize LLM here to avoid import-time side-effects
    # pylint: disable=line-too-long
    # pylint: disable=import-error
    from llama_cpp import Llama
    mp = model_path or os.path.join(BASE_DIR, 'models', 'aya-expanse-8b-Q4_K_M.gguf')
    llm = Llama(model_path=mp, n_ctx=8192, n_threads=2, verbose=False)

    os.makedirs(output_dir, exist_ok=True)

    with open(readme_path, 'r', encoding='utf-8') as f:
        content = f.read()

    translated_text = run_translation_pipeline(content, llm, lang, prompts, lang_guidance)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(translated_text)

    update_navbar_in_readme(readme_path, output_dir, lang)
    
    print(f'[SUCCESS] Wrote translated locales to {output_path} and injected navbar into {readme_path}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--lang", type=str, default="")
    parser.add_argument("--model-path", type=str, default="")
    parser.add_argument("--nav-target", type=str, default="README.md")
    parser.add_argument("--mode", type=str, default="translate")
    args = parser.parse_args()

    if args.mode == "translate" and not args.lang:
        parser.error("the following arguments are required: --lang")

    main(args.lang, model_path=args.model_path, nav_target=args.nav_target, mode=args.mode)
