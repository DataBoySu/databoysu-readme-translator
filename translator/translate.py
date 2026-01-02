"""
Translation module for the README translator action.
Handles chunking, translation via LLM, and navbar injection.
"""
import os
import re
import argparse

LANG_MAP = {
    "de": "German", "fr": "French", "es": "Spanish", "ja": "Japanese",
    "zh": "Chinese(Simplified)", 
    "ru": "Russian", "pt": "Portuguese", "ko": "Korean", "hi": "Hindi",
    # not fully checked
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
    "说明", "本节", "在这里", "意味着", "解释",
    # German
    "Dieser Abschnitt", "In diesem", "In diesem Abschnitt", "bedeutet", "erklärt",
    # French
    "Cette section", "Dans cette", "Dans cette section", "signifie", "explique",
    # Spanish
    "Esta sección", "En esta", "En esta sección", "significa", "explica",
    # Japanese
    "このセクション", "この中で", "このセクションでは", "意味する", "説明する", "顔を赤らめる",
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
    "說明", "本節", "在這裡", "意味著", "解釋",
    # Portuguese
    "Esta seção", "Nesta seção", "significa", "explica",
    # Korean
    "이 섹션", "이 안에서", "이 섹션에서는", "의미한다", "설명한다",
    # Hindi
    "यह अनुभाग", "इस अनुभाग में", "का अर्थ है", "समझाता है", "चिड़िया",
]

# Language-specific expansion multipliers for length validation
HIGH_MULTIPLIER_MAP = {
    # East Asian and high-expansion languages
    "ja": 5.5,    # Japanese (very compact source -> longer translations)
    "zh": 3.5,    # Chinese (Simplified)
    "zh-tw": 3.5, # Chinese (Traditional)

    # South Asian
    "hi": 5.5,    # Hindi

    # Right-to-left and morphologically rich languages
    "ar": 4.0,    # Arabic
    "he": 4.0,    # Hebrew
    "fa": 4.0,    # Persian (Farsi)

    # Slavic and other high-expansion languages
    "ru": 3.5,    # Russian
    "uk": 3.5,    # Ukrainian
    "pl": 3.5,    # Polish

    # Germanic / Romance
    "de": 3.5,    # German (compound nouns)
    "fr": 3.0,    # French
    "es": 3.0,    # Spanish
    "pt": 3.0,    # Portuguese
    "it": 3.0,    # Italian

    # Other European and SE Asian languages (moderate expansion)
    "nl": 2.5,    # Dutch
    "cs": 2.5,    # Czech
    "el": 2.5,    # Greek
    "ro": 2.5,    # Romanian
    "tr": 2.5,    # Turkish
    "vi": 2.5,    # Vietnamese
    "id": 2.5,    # Indonesian

    # Korean (can expand moderately)
    "ko": 3.0,

    # English - baseline (should not expand much)
    "en": 2.0,
}

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def _classify_text_as_struct_or_prose(text):
    """Classify text as 'struct' or 'prose' based on structural markers.

    Args:
        text (str): The text to classify.

    Returns:
        str: 'struct' if the text contains structural elements, 'prose' otherwise.
    """
    t = text.strip()
    if (
        t.startswith(('<div', '<details', '```')) or
        (t.startswith('<p') and not re.sub(r'<[^>]+>', '', t).strip()) or
        t.startswith('<!--') or t.endswith('-->') or
        re.match(r'!\[.*?\]\(.*?\)', t) or
        re.match(r'\[.*?\]\(.*?\)', t) or
        re.search(r'\[![^\]\[]+\]', t)
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

        # If the blockquote begins with a GitHub-style admonition token
        # like `[!NOTE]` or a localized variant (e.g., `[!WICHTIG]`),
        # treat the entire blockquote as `struct` so it is preserved
        # and not converted to a `prose` block for translation.
        first_bq_line = lines[start].lstrip()
        is_admonition_bq = bool(re.match(r'>\s*\[![^\]\[]+\]', first_bq_line)) or bool(re.search(r'\[![^\]\[]+\]', block))

        if before:
            out.append((_classify_text_as_struct_or_prose(before), before))

        if is_admonition_bq:
            out.append(('struct', block))
        else:
            out.append(('prose', block))

        if after:
            out.append((_classify_text_as_struct_or_prose(after), after))

    return out


def get_smart_chunks(text):
    """Split text into smart chunks based on markdown and HTML structures.

    Args:
        text (str): The input text to chunk.

    Returns:
        list: List of tuples (chunk_type, chunk_text) where chunk_type is 'struct' or 'prose'.
    """
    pattern = r'(' \
              r'```[\s\S]*?```|' \
              r'<div\b[^>]*>[\s\S]*?<\/div>|' \
              r'<p\b[^>]*>[\s\S]*?<\/p>|' \
              r'<details\b[^>]*>[\s\S]*?<\/details>|' \
              r'^#{1,6} .*' \
              r')'

    raw_parts = re.split(pattern, text, flags=re.MULTILINE | re.IGNORECASE)
    chunks = []

    for part in raw_parts:
        if not part or not part.strip():
            continue

        p = part.strip()

        # Treat GitHub-style admonition tokens like [!NOTE], [!IMPORTANT] as struct
        if re.search(r'\[![^\]\[]+\]', p):
            chunks.append(("struct", p))
            continue

        if re.match(r'^[-*_]{3,}$', p):
            chunks.append(("struct", p))
            continue

        # Treat Markdown image badges/links as struct (e.g., ![Lines of Code](...)).
        # Do this before classifying blockquotes as prose so badge lines inside
        # blockquotes are not misclassified.
        if re.match(r'!\[.*?\]\(.*?\)', p) or re.match(r'\[.*?\]\(.*?\)', p):
            chunks.append(("struct", p))
            continue

        if p.startswith('>') or p.startswith('*') or p.endswith('*') or p.startswith('> *') or p.startswith(' *'):
            chunks.append(("prose", p))
            continue
        
        if (
            p.startswith(('<div', '<details', '```')) or
            (p.startswith('<p') and not re.sub(r'<[^>]+>', '', p).strip()) or
            p.startswith('<!--') or p.endswith('-->') or
            re.match(r'!\[.*?\]\(.*?\)', p) or
            re.match(r'\[.*?\]\(.*?\)', p)
        ):
            chunks.append(("struct", p))
        else:
            chunks.append(("prose", p))

        # Ensure any struct chunks containing blockquotes are split
    try:
        return split_struct_blockquotes(chunks)
    except NameError:
        return chunks



def merge_small_chunks(chunks, min_chars=50):
    """Merge small prose chunks to optimize translation.

    Args:
        chunks (list): List of (type, text) tuples.
        min_chars (int): Minimum character count for a chunk to be considered large.

    Returns:
        list: Merged list of chunks.
    """
    merged = []
    i = 0
    while i < len(chunks):
        ctype, ctext = chunks[i]
        
        if ctype == "prose" and (ctext.startswith('#') or len(ctext) < min_chars) and i + 1 < len(chunks) and chunks[i+1][0] != "struct":
            next_ctype, next_ctext = chunks[i+1]
            combined_text = ctext + "\n\n" + next_ctext
            
            merged.append(("prose", combined_text))
            i += 2 
        else:
            merged.append((ctype, ctext))
            i += 1
    return merged

def strip_think_tokens(text):
    """Remove think tokens and collapse excessive blank lines.

    Args:
        text (str): The text to clean.

    Returns:
        str: Cleaned text.
    """
    if not text:
        return text
    # Remove the think block content entirely
    text = re.sub(r'<think\b[^>]*>[\s\S]*?<\/think>', '', text, flags=re.IGNORECASE)
    # Collapse excessive blank lines (3+ newlines -> 2 newlines)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text

def strip_garbage_lines(text):
    """Remove lines with garbage characters and short lines.

    Args:
        text (str): The text to clean.

    Returns:
        str: Cleaned text.
    """
    if not text:
        return text
    # 1. Remove lines containing specific garbage characters (ESC, RS, FS, SUB)
    text = re.sub(r'^.*[\x1b\x1e\x1c\x1a].*(\r?\n|\Z)', '', text, flags=re.MULTILINE)
    # 2. Remove lines that are 1 or 2 characters long (ignoring whitespace)
    text = re.sub(r'^[ \t]*[^\s>]{1,2}[ \t]*(\r?\n|\Z)', '', text, flags=re.MULTILINE)
    # 3. Collapse excessive blank lines again in case removal created gaps
    # text = re.sub(r'\n{3,}', '\n\n', text)
    return text

def fix_relative_paths(text):
    """Fix relative paths in links to point to parent directory.

    Args:
        text (str): The text containing links.

    Returns:
        str: Text with fixed paths.
    """
    text = re.sub(r'(\[.*?\]\()(?!(?:http|/|#|\.\./))', r'\1../', text) 
    text = re.sub(r'((?:src|href)=["\'])(?!(?:http|/|#|\.\./))', r'\1../', text)
    return text

def translate_chunk(text, llm, prompts, lang_guidance=None, is_lone_header=False):
    """Translate a single chunk of text using the LLM.

    Args:
        text (str): The text to translate.
        llm: The LLM instance.
        prompts (dict): Dictionary with 'header' and 'prose' prompts.
        lang_guidance (str, optional): Language-specific guidance.
        is_lone_header (bool): Whether this is a standalone header.

    Returns:
        str: Translated text.
    """


    # base_prompt = prompts['header'] if is_lone_header else prompts['prose']
    base_prompt = prompts['prose']
    system_content = f"{lang_guidance}\n\n{base_prompt}" if lang_guidance else base_prompt

    prompt = (
        f"<|im_start|>system\n/no_think{system_content}<|im_end|>\n"
        f"<|im_start|>user\n{text}<|im_end|>\n"
        f"<|im_start|>assistant\n"
    )

    estimated_limit = int(len(text) * 3) + 200
    gen_limit = min(4096, max(256, estimated_limit))

    response = llm(prompt, max_tokens=gen_limit, temperature=0, stop=["<|im_end|>"])
    translated = response['choices'][0]['text'].strip()
    
    translated = re.sub(r'<think>.*?</think>', '', translated, flags=re.DOTALL).strip()
    
    if translated.startswith("```") and translated.endswith("```"):
        lines = translated.splitlines()
        if len(lines) > 2: translated = "\n".join(lines[1:-1]).strip()

    return translated


def get_system_prompts(target_lang_name):
    """Generate system prompts for header and prose translation."""

    prose = (
    f"You are a professional technical translation engine for {target_lang_name}. "
    "Your output is piped directly into a production file; any deviation will break the system.\n\n"
    "Use <think> to start thinking and </think> to stop thinking. Both tags go together, do not output one, without the other in exact same sequence."
    "IMMUTABLE SYNTAX BLOCKS: Do not attempt to parse or 'fix' nested syntax; if a code block (```) exists inside a blockquote (>), preserve the exact line-start character sequence including all spaces. Do not wrap my translation in new backticks.\n"
    "### CRITICAL OUTPUT RULES:\n"
    "- Output ONLY the translated text. No introductions, no conversational filler, and no 'Here is the translation'.\n"
    "- STRICTLY FORBIDDEN: Do not add safety disclaimers, warnings, or 'Note:' prefixes regarding API keys or security.\n"
    "- If you add any text other than the raw translation, the system will crash.\n\n"
    
    "### DATA & CODE INTEGRITY:\n"
    "- NUMERICAL LOCKDOWN: NEVER translate or reformat numbers, units (hrs, mins, sec), or timestamps. Treat them as immutable code constants.\n"
    "- SACRED TOKENS: Treat text inside angle brackets (e.g., <Your GitHub Access Token>) as non-translatable code. Keep placeholders exactly as they appear.\n"
    "- TECHNICAL TERMS: Keep hardware and software identifiers (GPU, VRAM, CLI, Docker, GEMM, PIDs, NVLink) in English.\n\n"
    
    "### STRUCTURAL & MARKDOWN SYNTAX:\n"
    "- HTML BLACK BOX: NEVER modify HTML tags, attributes (href, src), or CSS styles. Translate only human-visible text between tags.\n"
    "- MARKDOWN SYMBOLS: Preserve all symbols (#, > *, **, `, -, [link](url)) exactly. Do not change list markers or emphasis styles.\n"
    "- BADGES: Do NOT translate or modify markdown image links/badges of the form ![alt](url).\n"
    "- ADMONITIONS: Do NOT translate bracketed tokens like [!NOTE], [!IMPORTANT], or [!WARNING]. Preserve case and brackets exactly.\n\n"
    
    "### FORMATTING & WHITESPACE:\n"
    "- Do NOT normalize, reflow, or 'fix' the input text. Preserve all original whitespace, punctuation, and line breaks exactly.\n"
    "- Translate human text only; leave surrounding technical symbols unchanged."      
    )
    return prose


def load_guidance(lang):
    """Load language-specific guidance from scripts directory.

    Args:
        lang (str): Language code.

    Returns:
        str: Guidance text or empty string if not found.
    """
    scripts_dir = os.path.join(BASE_DIR, "scripts")
    guidance_file = os.path.join(scripts_dir, f"{lang}.txt")
    if os.path.exists(guidance_file):
        with open(guidance_file, "r", encoding="utf-8") as f:
            content = f.read().strip()
        print(f"[INFO] Loaded guidance from {guidance_file}", flush=True)
        return content

    print(f"[INFO] No guidance file found for '{lang}' at {guidance_file}", flush=True)
    return ""


def process_chunks(chunks, llm, lang, prompts, lang_guidance):
    """Process and translate chunks, applying validation.

    Args:
        chunks (list): List of (type, text) tuples.
        llm: The LLM instance.
        lang (str): Target language code.
        prompts (dict): Prompts dictionary.
        lang_guidance (str): Language guidance.

    Returns:
        str: Processed text.
    """
    final_output = []
    multiplier = HIGH_MULTIPLIER_MAP.get(lang, 3.0)
    total = len(chunks)

    for i, (ctype, ctext) in enumerate(chunks):
        if ctype == 'struct' or not ctext.strip():
            final_output.append(ctext + '\n\n'); continue

        # Show the full chunk being translated for easier debugging and context
        print(f"[INFO] Translating chunk {i+1}/{total}:\n{ctext}\n---", flush=True)
        is_lone_header = ctext.strip().startswith('#') and '\n' not in ctext.strip()
        
        translated = translate_chunk(ctext, llm, prompts, lang_guidance, is_lone_header)

        # Pipeline Validation Logic
        if len(translated) > multiplier * len(ctext):
            print(f"[WARN] Length check failed on chunk {i+1}, reverting."); translated = ctext
        elif any(f in translated for f in FORBIDDEN):
            print(f"[WARN] Forbidden phrase detected in chunk {i+1}, Hallucination Warning!.")
        elif ("</div>" in ctext and "</div>" not in translated) or ("</details>" in ctext and "</details>" not in translated):
            print(f"[WARN] HTML structural loss in chunk {i+1}, reverting."); translated = ctext

        final_output.append(translated.rstrip() + '\n\n')

    return ''.join(final_output)

def run_translation_pipeline(content, llm, lang, prompts, lang_guidance):
    """Run the full translation pipeline on content.

    Args:
        content (str): The content to translate.
        llm: The LLM instance.
        lang (str): Target language.
        prompts (dict): Prompts.
        lang_guidance (str): Guidance.

    Returns:
        str: Translated content.
    """
    chunks = get_smart_chunks(content)
    chunks = merge_small_chunks(chunks)

    full_text = process_chunks(chunks, llm, lang, prompts, lang_guidance)
    
    # Cleaning Phase
    full_text = strip_think_tokens(full_text)
    full_text = strip_garbage_lines(full_text)
    full_text = fix_relative_paths(full_text)
    
    return full_text


def regenerate_all_navbars(readme_path, locales_dir):
    """Regenerate navigation bars for root and locale READMEs.

    Args:
        readme_path (str): Path to the root README.
        locales_dir (str): Path to the locales directory.
    """
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
    for lang in langs:
        update_file(os.path.join(locales_dir, f'README.{lang}.md'), locale_block)
    
    print(f"[SUCCESS] Regenerated navbars for Root and {len(langs)} locales.")


def main(lang, model_path='', nav_target='README.md', mode='translate'):
    """Main entry point for the translation script.

    Args:
        lang (str): Target language code.
        model_path (str): Path to the LLM model.
        nav_target (str): Path to the target README.
        mode (str): 'translate' or 'navbar'.
    """
    readme_path = os.path.abspath(nav_target)
    output_dir = os.path.join(os.getcwd(), "locales")

    if mode == 'navbar':
        regenerate_all_navbars(readme_path, output_dir); return

    from llama_cpp import Llama
    mp = model_path or os.path.join(BASE_DIR, 'models', 'Qwen3-14B-Q4_K_M.gguf')
    llm = Llama(model_path=mp, n_ctx=8192, n_threads=4, verbose=False)

    target_lang_name = LANG_MAP.get(lang, "English")
    header_prompt, prose_prompt = get_system_prompts(target_lang_name)
    
    lang_guidance = load_guidance(lang)

    os.makedirs(output_dir, exist_ok=True)
    with open(readme_path, 'r', encoding='utf-8') as f: content = f.read()

    translated_text = run_translation_pipeline(content, llm, lang, {'header': header_prompt, 'prose': prose_prompt}, lang_guidance)

    with open(os.path.join(output_dir, f"README.{lang}.md"), 'w', encoding='utf-8') as f:
        f.write(translated_text)

    regenerate_all_navbars(readme_path, output_dir)
    print(f'[SUCCESS] Translated locale for {lang} created.')


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
