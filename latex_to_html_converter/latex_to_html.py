#!/usr/bin/env python3
import os
import sys
import json
import base64
import shutil
import subprocess
import tempfile
import zipfile
import io
import webbrowser
import socket
import threading
import mimetypes
import re
import html
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn

# ----------------------------------------------------------------------
# Config & Paths
# ----------------------------------------------------------------------
DEFAULT_PORT = 8082

def get_pandoc_path():
    """Find pandoc on the system, checking common locations as fallbacks."""
    path = shutil.which('pandoc')
    if path:
        return path
    common_paths = [
        '/opt/homebrew/bin/pandoc',
        '/usr/local/bin/pandoc',
        '/usr/bin/pandoc',
        '/usr/local/macports/bin/pandoc'
    ]
    for p in common_paths:
        if os.path.exists(p):
            return p
    return None

def read_file_with_fallback(file_path):
    """Attempt to read a text file using multiple common encodings, falling back to utf-8 with errors ignored."""
    encodings = ['utf-8', 'latin-1', 'cp1252', 'utf-16']
    for enc in encodings:
        try:
            with open(file_path, 'r', encoding=enc) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        return f.read()


# ----------------------------------------------------------------------
# HTML CSS Themes
# ----------------------------------------------------------------------
THEMES = {
    'academic': {
        'name': 'Academic Paper',
        'css': """
            :root {
                --bg-color: #fcfcfc;
                --text-color: #1a1a1a;
                --title-color: #111111;
                --link-color: #0044ee;
                --border-color: #dddddd;
                --code-bg: #f4f4f4;
                --toc-bg: #fcfcfc;
                --toc-border: #dddddd;
                --toc-link: #111111;
                --toc-title: #111111;
            }
            body {
                font-family: "Georgia", "Times New Roman", Times, serif;
                line-height: 1.62;
                color: var(--text-color);
                background-color: var(--bg-color);
                max-width: 750px;
                margin: 50px auto;
                padding: 0 24px;
            }
            h1, h2, h3, h4, h5, h6 {
                font-family: "Georgia", serif;
                color: var(--title-color);
                margin-top: 1.6em;
                margin-bottom: 0.6em;
                font-weight: 600;
            }
            h1 { text-align: center; font-size: 2.2em; margin-bottom: 1.8em; line-height: 1.2; }
            h2 { border-bottom: 1px solid var(--border-color); padding-bottom: 0.3em; font-size: 1.6em; }
            h3 { font-size: 1.3em; }
            p { margin: 1.2em 0; text-align: justify; text-indent: 1.5em; }
            p:first-of-type, h1 + p, h2 + p, h3 + p { text-indent: 0; }
            code { font-family: "Courier New", Courier, monospace; background: var(--code-bg); padding: 2px 4px; border-radius: 3px; font-size: 0.9em; }
            pre { background: var(--code-bg); padding: 15px; border-left: 3px solid #b5b5b5; overflow-x: auto; border-radius: 4px; font-family: monospace; }
            table { border-collapse: collapse; width: 100%; margin: 2em 0; font-size: 0.95em; }
            th, td { border: 1px solid var(--border-color); padding: 10px; text-align: left; }
            th { background-color: #f2f2f2; font-weight: bold; }
            blockquote { border-left: 4px solid #b5b5b5; margin: 1.5em 0; padding: 0.5em 20px; color: #555555; font-style: italic; }
            img { max-width: 100%; height: auto; display: block; margin: 2em auto; box-shadow: 0 2px 8px rgba(0,0,0,0.05); }
            .math { overflow-x: auto; padding: 8px 0; }
            a { color: var(--link-color); text-decoration: none; }
            a:hover { text-decoration: underline; }
        """
    },
    'minimalist': {
        'name': 'Modern Minimalist',
        'css': """
            :root {
                --bg-color: #ffffff;
                --text-color: #334155;
                --title-color: #0f172a;
                --link-color: #2563eb;
                --border-color: #e2e8f0;
                --code-bg: #f8fafc;
                --toc-bg: #f8fafc;
                --toc-border: #e2e8f0;
                --toc-link: #475569;
                --toc-title: #0f172a;
            }
            body {
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
                line-height: 1.75;
                color: var(--text-color);
                background-color: var(--bg-color);
                max-width: 800px;
                margin: 60px auto;
                padding: 0 24px;
                -webkit-font-smoothing: antialiased;
            }
            h1, h2, h3, h4, h5, h6 {
                color: var(--title-color);
                font-weight: 600;
                margin-top: 2em;
                margin-bottom: 0.8em;
                letter-spacing: -0.02em;
            }
            h1 { font-size: 2.6em; line-height: 1.15; margin-bottom: 0.8em; font-weight: 700; }
            h2 { font-size: 1.8em; border-bottom: 1px solid var(--border-color); padding-bottom: 0.4em; }
            h3 { font-size: 1.4em; }
            p { margin: 1.25em 0; }
            code { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; background: var(--code-bg); padding: 0.2em 0.4em; border-radius: 6px; font-size: 0.85em; color: #0f172a; border: 1px solid #f1f5f9; }
            pre { background: var(--code-bg); border: 1px solid var(--border-color); padding: 20px; overflow-x: auto; border-radius: 8px; font-family: monospace; }
            table { border-collapse: collapse; width: 100%; margin: 2.5em 0; font-size: 0.9em; }
            th, td { border-bottom: 1px solid var(--border-color); padding: 12px 16px; text-align: left; }
            th { background-color: #f8fafc; font-weight: 600; color: var(--title-color); }
            blockquote { border-left: 4px solid var(--link-color); margin: 1.8em 0; padding: 0.5em 20px; color: #475569; background: #eff6ff; border-radius: 0 8px 8px 0; }
            img { max-width: 100%; height: auto; display: block; margin: 2.5em auto; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.06); }
            .math { overflow-x: auto; padding: 12px 0; }
            a { color: var(--link-color); text-decoration: none; transition: color 0.15s ease; }
            a:hover { color: #1d4ed8; text-decoration: underline; }
        """
    },
    'dark': {
        'name': 'Sleek Dark',
        'css': """
            :root {
                --bg-color: #0f172a;
                --text-color: #cbd5e1;
                --title-color: #f8fafc;
                --link-color: #38bdf8;
                --border-color: #334155;
                --code-bg: #1e293b;
                --toc-bg: #1e293b;
                --toc-border: #334155;
                --toc-link: #94a3b8;
                --toc-title: #f8fafc;
            }
            body {
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
                line-height: 1.75;
                color: var(--text-color);
                background-color: var(--bg-color);
                max-width: 800px;
                margin: 60px auto;
                padding: 0 24px;
            }
            h1, h2, h3, h4, h5, h6 {
                color: var(--title-color);
                font-weight: 600;
                margin-top: 2em;
                margin-bottom: 0.8em;
                letter-spacing: -0.015em;
            }
            h1 { font-size: 2.6em; line-height: 1.15; margin-bottom: 0.8em; font-weight: 700; text-shadow: 0 0 40px rgba(56, 189, 248, 0.15); }
            h2 { font-size: 1.8em; border-bottom: 1px solid var(--border-color); padding-bottom: 0.4em; }
            h3 { font-size: 1.4em; }
            p { margin: 1.25em 0; }
            code { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; background: var(--code-bg); padding: 0.2em 0.4em; border-radius: 6px; font-size: 0.85em; color: #38bdf8; border: 1px solid #1e293b; }
            pre { background: var(--code-bg); border: 1px solid var(--border-color); padding: 20px; overflow-x: auto; border-radius: 8px; font-family: monospace; }
            table { border-collapse: collapse; width: 100%; margin: 2.5em 0; font-size: 0.9em; }
            th, td { border-bottom: 1px solid var(--border-color); padding: 12px 16px; text-align: left; }
            th { background-color: #1e293b; font-weight: 600; color: var(--title-color); }
            blockquote { border-left: 4px solid var(--link-color); margin: 1.8em 0; padding: 0.5em 20px; color: #94a3b8; background: rgba(56, 189, 248, 0.05); border-radius: 0 8px 8px 0; }
            img { max-width: 100%; height: auto; display: block; margin: 2.5em auto; border-radius: 8px; filter: brightness(0.95); box-shadow: 0 4px 20px rgba(0,0,0,0.3); }
            .math { overflow-x: auto; padding: 12px 0; color: #f8fafc; }
            a { color: var(--link-color); text-decoration: none; transition: color 0.15s ease; }
            a:hover { color: #7dd3fc; text-decoration: underline; }
        """
    },
    'sepia': {
        'name': 'Warm Sepia',
        'css': """
            :root {
                --bg-color: #fbf6ec;
                --text-color: #433422;
                --title-color: #2c1a04;
                --link-color: #c2410c;
                --border-color: #e7dcc4;
                --code-bg: #f4ebd8;
                --toc-bg: #f4ebd8;
                --toc-border: #e7dcc4;
                --toc-link: #5c4327;
                --toc-title: #2c1a04;
            }
            body {
                font-family: 'Outfit', -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
                line-height: 1.8;
                color: var(--text-color);
                background-color: var(--bg-color);
                max-width: 780px;
                margin: 60px auto;
                padding: 0 24px;
            }
            h1, h2, h3, h4, h5, h6 {
                color: var(--title-color);
                font-weight: 600;
                margin-top: 2em;
                margin-bottom: 0.8em;
            }
            h1 { font-size: 2.6em; line-height: 1.15; margin-bottom: 0.8em; font-weight: 700; }
            h2 { font-size: 1.9em; border-bottom: 1px solid var(--border-color); padding-bottom: 0.4em; }
            h3 { font-size: 1.45em; }
            p { margin: 1.3em 0; }
            code { font-family: monospace; background: var(--code-bg); padding: 0.25em 0.4em; border-radius: 4px; font-size: 0.85em; color: #5c3c10; }
            pre { background: var(--code-bg); border: 1px solid var(--border-color); padding: 20px; overflow-x: auto; border-radius: 8px; font-family: monospace; }
            table { border-collapse: collapse; width: 100%; margin: 2.5em 0; }
            th, td { border-bottom: 1px solid var(--border-color); padding: 12px 16px; text-align: left; }
            th { background-color: #f4ebd8; font-weight: 600; color: var(--title-color); }
            blockquote { border-left: 4px solid var(--link-color); margin: 1.8em 0; padding: 0.5em 20px; color: #5c4327; background: #f7eddb; border-radius: 0 8px 8px 0; }
            img { max-width: 100%; height: auto; display: block; margin: 2.5em auto; border-radius: 8px; box-shadow: 0 4px 12px rgba(44, 26, 4, 0.08); }
            .math { overflow-x: auto; padding: 12px 0; }
            a { color: var(--link-color); text-decoration: none; }
            a:hover { color: #9a3412; text-decoration: underline; }
        """
    },
    'transparent': {
        'name': 'Sin Fondo (Transparente)',
        'css': """
            :root {
                --bg-color: transparent;
                --text-color: inherit;
                --title-color: inherit;
                --link-color: #2563eb;
                --border-color: #e2e8f0;
                --code-bg: rgba(0, 0, 0, 0.05);
                --toc-bg: transparent;
                --toc-border: #e2e8f0;
                --toc-link: inherit;
                --toc-title: inherit;
            }
            body {
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
                line-height: 1.75;
                color: var(--text-color);
                background-color: var(--bg-color);
                max-width: 800px;
                margin: 60px auto;
                padding: 0 24px;
                -webkit-font-smoothing: antialiased;
            }
            h1, h2, h3, h4, h5, h6 {
                color: var(--title-color);
                font-weight: 600;
                margin-top: 2em;
                margin-bottom: 0.8em;
                letter-spacing: -0.02em;
            }
            h1 { font-size: 2.6em; line-height: 1.15; margin-bottom: 0.8em; font-weight: 700; }
            h2 { font-size: 1.8em; border-bottom: 1px solid var(--border-color); padding-bottom: 0.4em; }
            h3 { font-size: 1.4em; }
            p { margin: 1.25em 0; }
            code { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; background: var(--code-bg); padding: 0.2em 0.4em; border-radius: 6px; font-size: 0.85em; }
            pre { background: var(--code-bg); border: 1px solid var(--border-color); padding: 20px; overflow-x: auto; border-radius: 8px; font-family: monospace; }
            table { border-collapse: collapse; width: 100%; margin: 2.5em 0; font-size: 0.9em; }
            th, td { border-bottom: 1px solid var(--border-color); padding: 12px 16px; text-align: left; }
            th { background-color: rgba(0, 0, 0, 0.02); font-weight: 600; color: var(--title-color); }
            blockquote { border-left: 4px solid var(--link-color); margin: 1.8em 0; padding: 0.5em 20px; color: inherit; background: rgba(37, 99, 235, 0.05); border-radius: 0 8px 8px 0; }
            img { max-width: 100%; height: auto; display: block; margin: 2.5em auto; border-radius: 8px; }
            .math { overflow-x: auto; padding: 12px 0; }
            a { color: var(--link-color); text-decoration: none; transition: color 0.15s ease; }
            a:hover { color: #1d4ed8; text-decoration: underline; }
        """
    }
}

SHARED_CSS_ADDON = """
/* Document Navigation Header */
.document-header {
    position: sticky;
    top: 0;
    z-index: 1000;
    background: var(--bg-color);
    border-bottom: 1px solid var(--border-color);
    padding: 12px 24px;
    margin-bottom: 30px;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
    display: flex;
    justify-content: center;
}
.document-nav {
    display: flex;
    gap: 20px;
    justify-content: center;
    flex-wrap: wrap;
}
.document-nav a {
    color: var(--text-color);
    font-weight: 500;
    font-size: 0.95em;
    text-decoration: none;
    padding: 6px 12px;
    border-radius: 6px;
    transition: all 0.2s ease;
}
.document-nav a:hover {
    color: var(--link-color);
    background: rgba(99, 102, 241, 0.1);
    text-decoration: none;
}

/* Front Matter Page Splitting & Separation */
.frontmatter-section {
    page-break-after: always;
    break-after: page;
    border-bottom: 2px dashed var(--border-color);
    padding-bottom: 60px;
    margin-bottom: 60px;
    min-height: 80vh;
    display: flex;
    flex-direction: column;
    justify-content: center;
    box-sizing: border-box;
}

.frontmatter-section.cover-page {
    align-items: center;
    text-align: center;
}

.frontmatter-section.title-page {
    text-align: center;
}

.frontmatter-section.copyright-page {
    text-align: center;
    font-size: 0.95em;
    color: var(--text-color);
    opacity: 0.8;
}

.frontmatter-section.dedication-page {
    text-align: center;
    font-style: italic;
    font-size: 1.1em;
}

.frontmatter-section.preface-page {
    justify-content: flex-start;
    line-height: 1.6;
}

/* Styled Table of Contents */
#TOC {
    background: var(--toc-bg);
    border: 1px solid var(--toc-border);
    border-radius: 8px;
    padding: 24px;
    margin: 30px 0 60px 0;
    box-shadow: 0 2px 6px rgba(0, 0, 0, 0.02);
    page-break-after: always;
    break-after: page;
    border-bottom: 2px dashed var(--border-color);
    padding-bottom: 60px;
}
#TOC h2, #TOC h3, #TOC header, #TOC .toc-title, #TOC-title, #TOC > h2 {
    display: none !important;
}
#TOC ul {
    list-style: none;
    padding-left: 20px;
    margin: 0;
}
#TOC > ul {
    padding-left: 0;
}
#TOC li {
    margin: 6px 0;
}
#TOC a {
    color: var(--toc-link);
    text-decoration: none;
    font-size: 0.95em;
}
#TOC a:hover {
    color: var(--link-color);
    text-decoration: underline;
}
#TOC::before {
    content: "Índice";
    font-weight: 600;
    font-size: 1.1em;
    display: block;
    margin-bottom: 14px;
    color: var(--toc-title);
    border-bottom: 1px solid var(--toc-border);
    padding-bottom: 8px;
}

/* MathJax Scrollbar Fix */
.math {
    overflow-x: auto;
    overflow-y: hidden;
}

@media print {
    .no-print, .document-header {
        display: none !important;
    }
}
"""

# ----------------------------------------------------------------------
# Backend Conversion Logic
# ----------------------------------------------------------------------
def preprocess_all_tex_files(extract_dir):
    """Scan all .tex files, build a global label map, and resolve \ref and \eqref citations."""
    import re
    tex_files = []
    for root, _, files in os.walk(extract_dir):
        for file in files:
            if file.endswith('.tex'):
                tex_files.append(os.path.join(root, file))
                
    label_map = {}
    equation_labels = set()
    
    sec_num = 0
    subsec_num = 0
    fig_num = 0
    tab_num = 0
    eq_num = 0
    
    # First pass: Parse all .tex files to build a global label map and find equation labels
    for tex_path in tex_files:
        try:
            content = read_file_with_fallback(tex_path)
            
            lines = content.split('\n')
            in_figure = False
            in_table = False
            in_equation = False
            
            for line in lines:
                line_no_comment = line.split('%')[0]
                
                if '\\begin{figure}' in line_no_comment:
                    in_figure = True
                    fig_num += 1
                elif '\\end{figure}' in line_no_comment:
                    in_figure = False
                elif '\\begin{table}' in line_no_comment:
                    in_table = True
                    tab_num += 1
                elif '\\end{table}' in line_no_comment:
                    in_table = False
                elif any(env in line_no_comment for env in ['\\begin{equation}', '\\begin{align}', '\\begin{gather}', '\\begin{multline}', '\\begin{eqnarray}', '\\begin{alignat}', '\\[', '$$']):
                    in_equation = True
                    eq_num += 1
                elif any(env in line_no_comment for env in ['\\end{equation}', '\\end{align}', '\\end{gather}', '\\end{multline}', '\\end{eqnarray}', '\\end{alignat}', '\\]', '$$']):
                    in_equation = False
                elif '\\section{' in line_no_comment or '\\section*{' in line_no_comment:
                    if '\\section*{' not in line_no_comment:
                        sec_num += 1
                        subsec_num = 0
                elif '\\subsection{' in line_no_comment or '\\subsection*{' in line_no_comment:
                    if '\\subsection*{' not in line_no_comment:
                        subsec_num += 1
                        
                label_match = re.search(r'\\label\{([^}]+)\}', line_no_comment)
                if label_match:
                    key = label_match.group(1)
                    if in_equation or key.startswith(('eq:', 'ecuacion:')):
                        equation_labels.add(key)
                    elif in_figure:
                        label_map[key] = f"{fig_num}"
                    elif in_table:
                        label_map[key] = f"{tab_num}"
                    else:
                        if subsec_num > 0:
                            label_map[key] = f"{sec_num}.{subsec_num}"
                        else:
                            label_map[key] = f"{sec_num}"
        except Exception as e:
            print(f"Error building label map for {tex_path}: {e}")
            
    # Second pass: Apply reference replacements in all .tex files
    for tex_path in tex_files:
        try:
            content = read_file_with_fallback(tex_path)
                
            def replace_ref(match):
                ref_type = match.group(1) # 'ref' or 'eqref'
                key = match.group(2)
                is_eqref = ref_type == 'eqref'
                
                is_eq = (key in equation_labels) or key.startswith(('eq:', 'ecuacion:'))
                if is_eq:
                    # Let MathJax resolve it dynamically in the browser (needs to be inside math delimiters)
                    return f"\\(\\{ref_type}{{{key}}}\\)"
                
                # Otherwise, resolve statically in Python
                val = label_map.get(key)
                if val:
                    return f"({val})" if is_eqref else val
                
                clean_key = key.split(':')[-1] if ':' in key else key
                return f"({clean_key})" if is_eqref else clean_key
                
            pattern = re.compile(r'\\(ref|eqref)\{([^}]+)\}')
            new_content = pattern.sub(replace_ref, content)
            
            with open(tex_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
        except Exception as e:
            print(f"Error applying references in {tex_path}: {e}")

def embed_images_in_html(html_content, base_dir):
    """Scan HTML for img tags and encode local files to base64 data URLs."""
    img_pattern = re.compile(r'<img\s+([^>]*?)src="([^"]+)"([^>]*?)>')
    
    def replace_img(match):
        attrs_before = match.group(1)
        src = match.group(2)
        attrs_after = match.group(3)
        
        # Keep absolute/external URLs as-is
        if src.startswith(('data:', 'http:', 'https:')):
            return match.group(0)
            
        img_path = os.path.normpath(os.path.join(base_dir, src))
        if os.path.exists(img_path) and os.path.isfile(img_path):
            try:
                mime_type, _ = mimetypes.guess_type(img_path)
                if not mime_type:
                    mime_type = "image/png"
                with open(img_path, 'rb') as img_file:
                    img_data = base64.b64encode(img_file.read()).decode('utf-8')
                return f'<img {attrs_before}src="data:{mime_type};base64,{img_data}"{attrs_after}>'
            except Exception as e:
                print(f"Error embedding image {src}: {e}")
        return match.group(0)
        
    return img_pattern.sub(replace_img, html_content)

def perform_conversion(zip_bytes, settings, cover_file_b64=None):
    """
    Extracts the zip, runs pandoc, post-processes the output HTML, 
    and packages the response.
    """
    pandoc_path = get_pandoc_path()
    if not pandoc_path:
        return {
            "success": False,
            "error": "Pandoc was not found on your system. Please install it using: brew install pandoc"
        }

    # Extract settings
    theme_key = settings.get('theme', 'academic')
    include_toc = settings.get('toc', True)
    equations_numbered = settings.get('equations', True)
    use_mathjax = settings.get('mathjax', True)
    format_mode = settings.get('format', 'single') # 'single' or 'zip'

    theme_css = THEMES.get(theme_key, THEMES['academic'])['css'] + SHARED_CSS_ADDON

    with tempfile.TemporaryDirectory() as temp_dir:
        # Save ZIP content to temp file and extract
        zip_path = os.path.join(temp_dir, 'input.zip')
        with open(zip_path, 'wb') as f:
            f.write(zip_bytes)
            
        extract_dir = os.path.join(temp_dir, 'extracted')
        os.makedirs(extract_dir, exist_ok=True)
        
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
        except Exception as e:
            return {"success": False, "error": f"Failed to extract ZIP archive: {str(e)}"}

        # Preprocess references in all .tex files
        preprocess_all_tex_files(extract_dir)

        # Find main.tex
        main_tex = None
        
        # 1. Search for main.tex exactly
        for root, _, files in os.walk(extract_dir):
            for file in files:
                if file.lower() == 'main.tex':
                    main_tex = os.path.join(root, file)
                    break
            if main_tex:
                break
                
        # 2. Search for any file containing \documentclass
        if not main_tex:
            for root, _, files in os.walk(extract_dir):
                for file in files:
                    if file.endswith('.tex'):
                        candidate = os.path.join(root, file)
                        try:
                            content = read_file_with_fallback(candidate)
                            if '\\documentclass' in content:
                                main_tex = candidate
                                break
                        except:
                            pass
                if main_tex:
                    break
                    
        # 3. Just take the first .tex file found
        if not main_tex:
            for root, _, files in os.walk(extract_dir):
                for file in files:
                    if file.endswith('.tex'):
                        main_tex = os.path.join(root, file)
                        break
                if main_tex:
                    break
                    
        if not main_tex:
            return {
                "success": False, 
                "error": "Could not find a valid .tex file inside the ZIP archive. Make sure there is at least one .tex document."
            }

        # Setup files for Pandoc execution
        tex_dir = os.path.dirname(main_tex)
        out_html_name = os.path.splitext(os.path.basename(main_tex))[0] + '.html'
        out_html_path = os.path.join(tex_dir, out_html_name)

        pandoc_cmd = [
            pandoc_path,
            os.path.basename(main_tex),
            '--from=latex',
            '--to=html5',
            '--standalone',
            '--wrap=preserve',
            '-o', out_html_name
        ]
        
        if use_mathjax:
            pandoc_cmd.append('--mathjax')
        if include_toc:
            pandoc_cmd.extend(['--toc', '--toc-depth=3'])

        # Execute Pandoc
        try:
            result = subprocess.run(
                pandoc_cmd,
                cwd=tex_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=30
            )
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "The conversion timed out (max 30s). Your LaTeX file might be too large."}
        except Exception as e:
            return {"success": False, "error": f"Error running Pandoc: {str(e)}"}

        if not os.path.exists(out_html_path):
            return {
                "success": False,
                "error": f"Pandoc failed to generate output. Error log:\n{result.stderr}"
            }

        # Read the generated HTML
        with open(out_html_path, 'r', encoding='utf-8') as f:
            html_content = f.read()

        # Detect and enhance Bibliography / References section
        has_bib = False
        bib_id = None
        
        # Pandoc usually generates bibliography inside id="refs", class="references", or class="thebibliography"
        bib_match = re.search(r'(<div[^>]*id="refs"[^>]*>|<section[^>]*class="references"[^>]*>|<div[^>]*class="references"[^>]*>|<div[^>]*class="thebibliography"[^>]*>)', html_content, re.IGNORECASE)
        if bib_match:
            has_bib = True
            id_attr = re.search(r'id="([^"]*)"', bib_match.group(1), re.IGNORECASE)
            
            # If the container has no ID, we inject id="refs"
            if id_attr:
                bib_id = id_attr.group(1)
                bib_tag_modified = bib_match.group(1)
            else:
                bib_id = "refs"
                tag_name = "section" if "section" in bib_match.group(1).lower() else "div"
                bib_tag_modified = bib_match.group(1).replace(f"<{tag_name}", f"<{tag_name} id=\"{bib_id}\"")
                html_content = html_content.replace(bib_match.group(1), bib_tag_modified)
            
            # Check if there is already a heading containing "Bibliografía", "Referencias", "Bibliography" or "References"
            container_start = html_content.find(bib_tag_modified)
            search_prefix = html_content[max(0, container_start - 300):container_start]
            
            heading_exists = re.search(r'<h[1-6][^>]*>(?:Bibliografía|Referencias|Bibliography|References)</h[1-6]>', search_prefix, re.IGNORECASE)
            if not heading_exists:
                # Inject a beautiful heading before the container
                bib_heading = f'<h2 id="{bib_id}-heading" class="bibliography-heading" style="border-top: 1px solid var(--border-color); padding-top: 40px; margin-top: 60px;">Bibliografía</h2>'
                html_content = html_content.replace(bib_tag_modified, f"{bib_heading}\n{bib_tag_modified}")
                bib_id = f"{bib_id}-heading"
        else:
            # Fallback check for any heading containing bibliography keywords
            bib_header_match = re.search(r'<(h[1-6])\s+[^>]*id="([^"]*)"[^>]*>(?:Bibliografía|Referencias|Bibliography|References)</\1>', html_content, re.IGNORECASE)
            if bib_header_match:
                has_bib = True
                bib_id = bib_header_match.group(2)

        # 1. Detect and temporarily remove TOC
        toc_match = re.search(r'<(nav|div)\s+[^>]*id="TOC"[^>]*>', html_content, re.IGNORECASE)
        toc_html = ""
        if toc_match:
            tag = toc_match.group(1)
            open_tags = 1
            pos = toc_match.end()
            while open_tags > 0 and pos < len(html_content):
                next_open = html_content.find(f'<{tag}', pos)
                next_close = html_content.find(f'</{tag}>', pos)
                if next_close == -1:
                    break
                if next_open != -1 and next_open < next_close:
                    open_tags += 1
                    pos = next_open + len(tag) + 1
                else:
                    open_tags -= 1
                    pos = next_close + len(tag) + 3
            toc_html = html_content[toc_match.start():pos]
            html_content = html_content[:toc_match.start()] + html_content[pos:]

        # 2. Find the first chapter heading in the remaining HTML
        def get_first_chapter_idx(html):
            for h_match in re.finditer(r'<h([12])\b[^>]*>(.*?)</h\1>', html, re.IGNORECASE | re.DOTALL):
                h_text = re.sub(r'<[^>]*>', '', h_match.group(2)).strip().lower()
                is_frontmatter_heading = any(kw in h_text for kw in ['portada', 'presentación', 'presentacion', 'copyright', 'derechos de autor', 'dedicatoria', 'dedication', 'prefacio', 'preludio', 'prólogo', 'prologo', 'preface'])
                if not is_frontmatter_heading:
                    return h_match.start()
            return len(html)

        # Extract front matter sections directly from HTML if they were present in the LaTeX document
        extracted_frontmatter = {
            'cover': None,
            'copyright': None,
            'dedication': None,
            'preface': None
        }

        def extract_section_by_keyword(html, keywords, max_idx=None):
            if max_idx is None:
                max_idx = len(html)
            heading_pattern = r'(<h([1-6])\b[^>]*>(.*?)</h\2>)'
            for match in re.finditer(heading_pattern, html[:max_idx], re.IGNORECASE | re.DOTALL):
                full_heading_tag = match.group(1)
                heading_level = match.group(2)
                heading_content = match.group(3)
                
                # Check text content
                text_content = re.sub(r'<[^>]*>', '', heading_content).strip().lower()
                
                # Check attributes like id of the heading
                id_match = re.search(r'id="([^"]*)"', full_heading_tag, re.IGNORECASE)
                heading_id = id_match.group(1).lower() if id_match else ""
                
                # Check if any keyword matches
                matched = False
                for kw in keywords:
                    kw_lower = kw.lower()
                    if kw_lower in text_content or kw_lower in heading_id:
                        matched = True
                        break
                
                if matched:
                    start_idx = match.start()
                    
                    # Check if there is a preceding open section/div tag that wraps this section.
                    prefix = html[max(0, start_idx - 150):start_idx]
                    wrapper_match = re.search(r'(<(section|div)\s+[^>]*id="([^"]*)"[^>]*>)\s*$', prefix, re.IGNORECASE | re.DOTALL)
                    
                    is_wrapped = False
                    if wrapper_match:
                        wrapper_id = wrapper_match.group(3).lower()
                        if wrapper_id == heading_id or any(kw.lower() in wrapper_id for kw in keywords):
                            start_idx = start_idx - len(wrapper_match.group(0))
                            is_wrapped = True
                    
                    search_start = match.start() + len(full_heading_tag)
                    
                    # Find where the section ends
                    boundary_pattern = r'<(h[1-6]|header|footer|div\s+id="refs"|div\s+class="thebibliography"|section|div\s+id="TOC"|nav\s+id="TOC")\b'
                    next_boundary_match = re.search(boundary_pattern, html[search_start:], re.IGNORECASE)
                    
                    if next_boundary_match:
                        end_idx = search_start + next_boundary_match.start()
                    else:
                        body_end_match = re.search(r'</body[^>]*>', html[search_start:], re.IGNORECASE)
                        if body_end_match:
                            end_idx = search_start + body_end_match.start()
                        else:
                            end_idx = len(html)
                    
                    section_html = html[start_idx:end_idx].strip()
                    cleaned_html = html[:start_idx] + html[end_idx:]
                    return cleaned_html, section_html
                    
            return html, None

        def extract_div_by_class_or_content(html, class_name, keywords=None, max_idx=None):
            if max_idx is None:
                max_idx = len(html)
            pattern = rf'(<div\s+[^>]*class="[^"]*\b{class_name}\b[^"]*"[^>]*>)'
            for match in re.finditer(pattern, html[:max_idx], re.IGNORECASE):
                start_idx = match.start()
                open_divs = 1
                pos = match.end()
                while open_divs > 0 and pos < len(html):
                    next_open = html.find('<div', pos)
                    next_close = html.find('</div>', pos)
                    
                    if next_close == -1:
                        break
                        
                    if next_open != -1 and next_open < next_close:
                        open_divs += 1
                        pos = next_open + 4
                    else:
                        open_divs -= 1
                        pos = next_close + 6
                
                div_html = html[start_idx:pos]
                
                if keywords:
                    div_text = re.sub(r'<[^>]*>', '', div_html).lower()
                    matched = any(kw.lower() in div_text for kw in keywords)
                    if not matched:
                        continue
                        
                cleaned_html = html[:start_idx] + html[pos:]
                return cleaned_html, div_html
                
            return html, None

        # 1. Extract cover page
        # Try to extract by title-block-header first
        cover_match = re.search(r'(<header\s+[^>]*id="title-block-header"[^>]*>.*?</header>)', html_content, re.IGNORECASE | re.DOTALL)
        if cover_match:
            extracted_frontmatter['cover'] = cover_match.group(1)
            html_content = html_content.replace(cover_match.group(1), '')
        else:
            # Try to extract by header keywords
            first_chapter_idx = get_first_chapter_idx(html_content)
            html_content, sec_content = extract_section_by_keyword(html_content, ['portada', 'presentación', 'presentacion', 'hoja de presentación', 'hoja de presentacion'], max_idx=first_chapter_idx)
            if sec_content:
                extracted_frontmatter['cover'] = sec_content
            else:
                # Try by class "center" at the beginning of the body
                first_chapter_idx = get_first_chapter_idx(html_content)
                html_content, sec_content = extract_div_by_class_or_content(html_content, 'center', max_idx=first_chapter_idx)
                if sec_content:
                    extracted_frontmatter['cover'] = sec_content

        # 2. Extract Copyright
        first_chapter_idx = get_first_chapter_idx(html_content)
        html_content, sec_content = extract_section_by_keyword(html_content, ['copyright', 'derechos de autor', 'derechos-de-autor'], max_idx=first_chapter_idx)
        if sec_content:
            extracted_frontmatter['copyright'] = sec_content
        else:
            # Try by class "flushleft" containing copyright keywords
            first_chapter_idx = get_first_chapter_idx(html_content)
            html_content, sec_content = extract_div_by_class_or_content(html_content, 'flushleft', ['copyright', 'derechos', 'copying', '©'], max_idx=first_chapter_idx)
            if sec_content:
                extracted_frontmatter['copyright'] = sec_content

        # 3. Extract Dedication
        first_chapter_idx = get_first_chapter_idx(html_content)
        html_content, sec_content = extract_section_by_keyword(html_content, ['dedicatoria', 'dedication'], max_idx=first_chapter_idx)
        if sec_content:
            extracted_frontmatter['dedication'] = sec_content
        else:
            # Try by class "flushright" containing dedication keywords
            first_chapter_idx = get_first_chapter_idx(html_content)
            html_content, sec_content = extract_div_by_class_or_content(html_content, 'flushright', ['dedica', 'dedica', 'madre', 'padre', 'hermano', 'amor', 'corazón', 'corazon'], max_idx=first_chapter_idx)
            if not sec_content:
                first_chapter_idx = get_first_chapter_idx(html_content)
                html_content, sec_content = extract_div_by_class_or_content(html_content, 'flushright', max_idx=first_chapter_idx)
            if sec_content:
                extracted_frontmatter['dedication'] = sec_content

        # 4. Extract Preface
        first_chapter_idx = get_first_chapter_idx(html_content)
        html_content, sec_content = extract_section_by_keyword(html_content, ['prefacio', 'preludio', 'prólogo', 'prologo', 'preface'], max_idx=first_chapter_idx)
        if sec_content:
            extracted_frontmatter['preface'] = sec_content

        # Generate front matter sections (Cover, Copyright, Dedication, Preface)
        front_matter_html = ""
        header_nav_links = []
        
        # Cover Image / Title Page
        cover_html = ""
        if cover_file_b64:
            cover_mime = "image/png"
            if cover_file_b64.startswith("data:image/jpeg") or cover_file_b64.startswith("/9j/"):
                cover_mime = "image/jpeg"
            cover_html = f"""
            <section id="cover-page" class="frontmatter-section cover-page">
                <img src="data:{cover_mime};base64,{cover_file_b64}" style="max-width: 100%; max-height: 80vh; border-radius: 8px; box-shadow: 0 4px 20px rgba(0,0,0,0.15);" />
            </section>
            """
        elif extracted_frontmatter['cover']:
            inner_cover = re.sub(r'^<header[^>]*>|</header>$', '', extracted_frontmatter['cover'], flags=re.IGNORECASE | re.DOTALL)
            cover_html = f"""
            <section id="cover-page" class="frontmatter-section title-page">
                {inner_cover}
            </section>
            """
        elif settings.get('title') or settings.get('author') or settings.get('publisher'):
            title = settings.get('title', '').strip()
            author = settings.get('author', '').strip()
            publisher = settings.get('publisher', '').strip()
            if title:
                cover_html = f"""
                <section id="cover-page" class="frontmatter-section title-page">
                    <h1 style="font-size: 2.5em; font-weight: bold; margin-bottom: 10px; color: var(--toc-title, #111);">{html.escape(title)}</h1>
                    {f'<p style="font-size: 1.3em; font-style: italic; margin-top: 20px; color: #475569;">{html.escape(author)}</p>' if author else ''}
                    {f'<p style="font-size: 1em; color: #64748b; margin-top: 40px;">{html.escape(publisher)}</p>' if publisher else ''}
                    <hr style="width: 80px; margin: 40px auto; border: 0; border-top: 2px solid var(--link-color, #6366f1);" />
                </section>
                """
        
        if cover_html:
            front_matter_html += cover_html

        # Copyright Page
        copyright_html = ""
        if extracted_frontmatter['copyright']:
            copyright_html = f"""
            <section id="copyright-page" class="frontmatter-section copyright-page">
                {extracted_frontmatter['copyright']}
            </section>
            """
        else:
            book_copyright = settings.get('copyright', '').strip()
            if book_copyright:
                copyright_paras = []
                for p in book_copyright.split('\n\n'):
                    if p.strip():
                        lines = p.split('\n')
                        para_content = "<br/>".join(html.escape(line) for line in lines)
                        copyright_paras.append(f"<p>{para_content}</p>")
                copyright_text = "\n".join(copyright_paras)
                copyright_html = f"""
                <section id="copyright-page" class="frontmatter-section copyright-page">
                    {copyright_text}
                </section>
                """
                
        if copyright_html:
            front_matter_html += copyright_html

        # Dedicatoria Page
        dedication_html = ""
        if extracted_frontmatter['dedication']:
            dedication_html = f"""
            <section id="dedication-page" class="frontmatter-section dedication-page">
                {extracted_frontmatter['dedication']}
            </section>
            """
        else:
            book_dedication = settings.get('dedication', '').strip()
            if book_dedication:
                dedication_paras = []
                for p in book_dedication.split('\n\n'):
                    if p.strip():
                        lines = p.split('\n')
                        para_content = "<br/>".join(html.escape(line) for line in lines)
                        dedication_paras.append(f"<p>{para_content}</p>")
                dedication_text = "\n".join(dedication_paras)
                dedication_html = f"""
                <section id="dedication-page" class="frontmatter-section dedication-page">
                    {dedication_text}
                </section>
                """
                
        if dedication_html:
            front_matter_html += dedication_html

        # Preface Page
        preface_html = ""
        if extracted_frontmatter['preface']:
            preface_html = f"""
            <section id="preface-page" class="frontmatter-section preface-page">
                {extracted_frontmatter['preface']}
            </section>
            """
        else:
            book_preface = settings.get('preface', '').strip()
            if book_preface:
                preface_paras = []
                for p in book_preface.split('\n\n'):
                    if p.strip():
                        lines = p.split('\n')
                        para_content = "<br/>".join(html.escape(line) for line in lines)
                        preface_paras.append(f"<p>{para_content}</p>")
                preface_text = "\n".join(preface_paras)
                preface_html = f"""
                <section id="preface-page" class="frontmatter-section preface-page">
                    <h2 style="text-align: center; font-size: 1.8em; margin-bottom: 1.2em; color: var(--toc-title, #111);">Prefacio</h2>
                    {preface_text}
                </section>
                """
                
        if preface_html:
            front_matter_html += preface_html

        # Inject into HTML body (front matter first, then Table of Contents)
        if front_matter_html or toc_html:
            body_match = re.search(r'(<body[^>]*>)', html_content, re.IGNORECASE)
            if body_match:
                body_tag = body_match.group(1)
                injected_content = ""
                if front_matter_html:
                    injected_content += f"\n{front_matter_html}"
                if toc_html:
                    injected_content += f"\n{toc_html}"
                html_content = html_content.replace(body_tag, f"{body_tag}{injected_content}")

        # ----------------------------------------------------------------------
        # Post-Processing
        # ----------------------------------------------------------------------
        # 1. Inject MathJax config if needed
        if use_mathjax:
            mathjax_config = f"""
            <script>
            window.MathJax = {{
              tex: {{
                tags: '{'ams' if equations_numbered else 'none'}',
                inlineMath: [['$', '$'], ['\\\\(', '\\\\)']],
                displayMath: [['$$', '$$'], ['\\\\[', '\\\\]']],
                processEscapes: true
              }},
              options: {{
                ignoreHtmlClass: 'tex2jax_ignore',
                processHtmlClass: 'tex2jax_process'
              }}
            }};
            </script>
            """
            html_content = html_content.replace('<head>', f'<head>\n{mathjax_config}')

        # 2. Inject Custom Theme Styles
        styled_tag = f"<style>\n{theme_css}\n</style>"
        html_content = html_content.replace('</head>', f'{styled_tag}\n</head>')

        # 3. Handle PDF figure warning injection
        pdf_warning = ""
        pdf_refs = re.findall(r'src="([^"]+\.pdf)"', html_content)
        if pdf_refs:
            pdf_warning = (
                f"Warning: Found {len(pdf_refs)} PDF-based figure references. "
                "Web browsers cannot natively render PDF images. Please consider "
                "converting them to PNG or SVG in your LaTeX source."
            )

        # 4. Save and return results based on requested formatting mode
        saved_local_path = None
        zip_bytes = None
        zip_out_name = None
        
        if format_mode == 'single':
            # Embed all image assets inside the HTML as base64
            html_content = embed_images_in_html(html_content, tex_dir)
            b64_output = base64.b64encode(html_content.encode('utf-8')).decode('utf-8')
        else: # ZIP mode
            # Overwrite HTML file with our post-processed version
            with open(out_html_path, 'w', encoding='utf-8') as f:
                f.write(html_content)

            # Zip the entire extracted folder except original LaTeX source files
            excluded_exts = {'.tex', '.bib', '.cls', '.sty', '.aux', '.log', '.out', '.toc', '.synctex.gz', '.bbl', '.blg', '.zip'}
            
            output_zip_io = io.BytesIO()
            with zipfile.ZipFile(output_zip_io, 'w', zipfile.ZIP_DEFLATED) as out_zip:
                for root, _, files in os.walk(extract_dir):
                    for file in files:
                        _, ext = os.path.splitext(file)
                        if ext.lower() in excluded_exts:
                            continue
                        full_path = os.path.join(root, file)
                        rel_path = os.path.relpath(full_path, extract_dir)
                        out_zip.write(full_path, rel_path)
            
            output_zip_io.seek(0)
            zip_bytes = output_zip_io.read()
            b64_output = base64.b64encode(zip_bytes).decode('utf-8')
            zip_out_name = os.path.splitext(os.path.basename(main_tex))[0] + '_html.zip'

        # Auto-save local copy directly to Downloads folder
        try:
            home_dir = os.path.expanduser('~')
            downloads_dir = os.path.join(home_dir, 'Downloads')
            if os.path.exists(downloads_dir):
                target_filename = out_html_name if format_mode == 'single' else zip_out_name
                target_path = os.path.join(downloads_dir, target_filename)
                
                if format_mode == 'single':
                    with open(target_path, 'w', encoding='utf-8') as out_f:
                        out_f.write(html_content)
                else:
                    with open(target_path, 'wb') as out_f:
                        out_f.write(zip_bytes)
                saved_local_path = target_path
                print(f"[SERVIDOR] Archivo guardado localmente en descargas: {target_path}")
        except Exception as save_err:
            print(f"[AVISO] No se pudo guardar la copia en Downloads: {save_err}")

        if format_mode == 'single':
            return {
                "success": True,
                "filename": out_html_name,
                "file_data": b64_output,
                "mime_type": "text/html",
                "warning": pdf_warning,
                "logs": result.stderr,
                "saved_local_path": saved_local_path
            }
        else:
            return {
                "success": True,
                "filename": zip_out_name,
                "file_data": b64_output,
                "mime_type": "application/zip",
                "warning": pdf_warning,
                "logs": result.stderr,
                "saved_local_path": saved_local_path
            }

# ----------------------------------------------------------------------
# Local Server Implementation
# ----------------------------------------------------------------------
class RequestHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Silence default terminal request logs to keep output clean
        pass

    def do_GET(self):
        if self.path in ('/', '/index.html'):
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(FRONTEND_HTML.encode('utf-8'))
        elif self.path == '/status':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "running"}).encode('utf-8'))
        else:
            self.send_error(404, 'File Not Found')

    def do_POST(self):
        if self.path == '/convert':
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                self.send_error(400, 'Empty Request')
                return

            try:
                body = self.rfile.read(content_length).decode('utf-8')
                request_data = json.loads(body)
                
                # Retrieve parameters
                b64_zip = request_data.get('zip_file', '')
                b64_cover = request_data.get('cover_file', '')
                settings = request_data.get('settings', {})
                
                if not b64_zip:
                    self.send_response(400)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({"success": False, "error": "No ZIP data provided"}).encode('utf-8'))
                    return
                
                # Decode zip bytes
                zip_data = base64.b64decode(b64_zip)
                
                # Perform compilation
                response_data = perform_conversion(zip_data, settings, b64_cover)
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(response_data).encode('utf-8'))
                
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": f"Internal server error: {str(e)}"}).encode('utf-8'))
        else:
            self.send_error(404, 'API Endpoint Not Found')

class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True

# ----------------------------------------------------------------------
# Frontend HTML String (Embedded App UI)
# ----------------------------------------------------------------------
FRONTEND_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LaTeX to HTML Converter</title>
    <!-- Google Fonts -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-dark: #0b0f19;
            --card-bg: rgba(17, 24, 39, 0.7);
            --border-glow: rgba(99, 102, 241, 0.2);
            --accent-glow: linear-gradient(135deg, #6366f1 0%, #a855f7 100%);
            --accent-glow-hover: linear-gradient(135deg, #4f46e5 0%, #9333ea 100%);
            --text-main: #f3f4f6;
            --text-muted: #9ca3af;
            --indigo-solid: #6366f1;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            font-family: 'Outfit', sans-serif;
            background-color: var(--bg-dark);
            color: var(--text-main);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            overflow-x: hidden;
            position: relative;
        }

        /* Decorative blur backgrounds */
        body::before {
            content: '';
            position: absolute;
            width: 400px;
            height: 400px;
            background: rgba(99, 102, 241, 0.15);
            border-radius: 50%;
            filter: blur(80px);
            top: -100px;
            left: -100px;
            z-index: -1;
        }

        body::after {
            content: '';
            position: absolute;
            width: 400px;
            height: 400px;
            background: rgba(168, 85, 247, 0.12);
            border-radius: 50%;
            filter: blur(80px);
            bottom: -100px;
            right: -100px;
            z-index: -1;
        }

        header {
            margin-top: 40px;
            margin-bottom: 30px;
            text-align: center;
        }

        header h1 {
            font-size: 2.5em;
            font-weight: 700;
            background: linear-gradient(to right, #818cf8, #c084fc);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 8px;
            letter-spacing: -0.02em;
        }

        header p {
            font-size: 1.05em;
            color: var(--text-muted);
            max-width: 600px;
            padding: 0 20px;
        }

        .container {
            width: 90%;
            max-width: 1100px;
            display: grid;
            grid-template-columns: 1fr;
            gap: 30px;
            margin-bottom: 50px;
            z-index: 10;
        }

        @media (min-width: 900px) {
            .container {
                grid-template-columns: 420px 1fr;
            }
        }

        .card {
            background: var(--card-bg);
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 20px;
            padding: 28px;
            box-shadow: 0 10px 30px 0 rgba(0, 0, 0, 0.3);
            display: flex;
            flex-direction: column;
            transition: all 0.3s ease;
        }

        .card:hover {
            border-color: rgba(99, 102, 241, 0.2);
            box-shadow: 0 10px 40px 0 rgba(99, 102, 241, 0.05);
        }

        /* Drag and Drop Zone */
        .dropzone {
            border: 2px dashed rgba(255, 255, 255, 0.15);
            border-radius: 16px;
            padding: 35px 20px;
            text-align: center;
            cursor: pointer;
            transition: all 0.2s ease;
            position: relative;
            background: rgba(255, 255, 255, 0.02);
            margin-bottom: 24px;
        }

        .dropzone:hover, .dropzone.dragover {
            border-color: var(--indigo-solid);
            background: rgba(99, 102, 241, 0.06);
            box-shadow: 0 0 15px rgba(99, 102, 241, 0.1) inset;
        }

        .dropzone svg {
            width: 48px;
            height: 48px;
            margin-bottom: 12px;
            color: var(--text-muted);
            transition: color 0.2s ease;
        }

        .dropzone:hover svg, .dropzone.dragover svg {
            color: #818cf8;
            transform: translateY(-2px);
        }

        .dropzone input {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            opacity: 0;
            cursor: pointer;
        }

        .file-info {
            display: none;
            align-items: center;
            justify-content: center;
            gap: 10px;
            background: rgba(99, 102, 241, 0.1);
            border: 1px solid rgba(99, 102, 241, 0.3);
            border-radius: 10px;
            padding: 10px;
            margin-top: 10px;
            animation: fadeIn 0.3s ease;
        }

        .file-info svg {
            width: 20px;
            height: 20px;
            color: #4ade80;
        }

        .file-info-text {
            font-size: 0.9em;
            font-weight: 500;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            max-width: 250px;
        }

        .file-clear {
            cursor: pointer;
            color: var(--text-muted);
            margin-left: auto;
        }

        .file-clear:hover {
            color: #f87171;
        }

        /* Config Form */
        .setting-group {
            margin-bottom: 20px;
        }

        .setting-label {
            display: block;
            font-size: 0.9em;
            font-weight: 600;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 8px;
        }

        /* Themes Selection grid */
        .themes-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 10px;
        }

        .theme-btn {
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            padding: 12px;
            color: var(--text-main);
            font-family: inherit;
            font-size: 0.9em;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s ease;
            text-align: center;
        }

        .theme-btn:hover {
            background: rgba(255, 255, 255, 0.08);
            border-color: rgba(255, 255, 255, 0.2);
        }

        .theme-btn.active {
            border-color: var(--indigo-solid);
            background: rgba(99, 102, 241, 0.15);
            color: #a5b4fc;
            box-shadow: 0 0 12px rgba(99, 102, 241, 0.15);
        }

        /* Toggles layout */
        .toggle-row {
            display: flex;
            align-items: center;
            justify-content: space-between;
            background: rgba(255, 255, 255, 0.02);
            border: 1px solid rgba(255, 255, 255, 0.05);
            border-radius: 12px;
            padding: 12px 16px;
            margin-bottom: 10px;
            transition: border-color 0.2s;
        }

        .toggle-row:hover {
            border-color: rgba(255, 255, 255, 0.1);
        }

        .toggle-info {
            display: flex;
            flex-direction: column;
            gap: 2px;
        }

        .toggle-title {
            font-size: 0.95em;
            font-weight: 500;
        }

        .toggle-desc {
            font-size: 0.8em;
            color: var(--text-muted);
        }

        .switch {
            position: relative;
            display: inline-block;
            width: 44px;
            height: 24px;
            flex-shrink: 0;
        }

        .switch input {
            opacity: 0;
            width: 0;
            height: 0;
        }

        .slider {
            position: absolute;
            cursor: pointer;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background-color: #374151;
            transition: .3s;
            border-radius: 24px;
        }

        .slider:before {
            position: absolute;
            content: "";
            height: 18px;
            width: 18px;
            left: 3px;
            bottom: 3px;
            background-color: white;
            transition: .3s;
            border-radius: 50%;
        }

        input:checked + .slider {
            background: var(--accent-glow);
        }

        input:checked + .slider:before {
            transform: translateX(20px);
        }

        /* Format selector */
        .format-select {
            width: 100%;
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            padding: 12px 16px;
            color: var(--text-main);
            font-family: inherit;
            font-size: 0.95em;
            outline: none;
            cursor: pointer;
            appearance: none;
            -webkit-appearance: none;
            background-image: url("data:image/svg+xml;utf8,<svg fill='white' height='24' viewBox='0 0 24 24' width='24' xmlns='http://www.w3.org/2000/svg'><path d='M7 10l5 5 5-5z'/></svg>");
            background-repeat: no-repeat;
            background-position: right 12px center;
        }

        .format-select:focus {
            border-color: var(--indigo-solid);
            background-color: rgba(17, 24, 39, 0.95);
        }

        /* Convert Button */
        .btn-convert {
            width: 100%;
            background: var(--accent-glow);
            border: none;
            border-radius: 14px;
            padding: 16px;
            color: white;
            font-family: inherit;
            font-size: 1.1em;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s ease;
            box-shadow: 0 4px 15px rgba(139, 92, 246, 0.25);
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
            margin-top: 15px;
        }

        .btn-convert:hover:not(:disabled) {
            background: var(--accent-glow-hover);
            box-shadow: 0 4px 20px rgba(139, 92, 246, 0.4);
            transform: translateY(-1px);
        }

        .btn-convert:active:not(:disabled) {
            transform: translateY(1px);
        }

        .btn-convert:disabled {
            background: #374151;
            color: #6b7280;
            box-shadow: none;
            cursor: not-allowed;
        }

        /* Preview card & actions */
        .preview-card {
            display: flex;
            flex-direction: column;
            height: 100%;
            min-height: 550px;
        }

        .preview-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 15px;
            flex-wrap: wrap;
            gap: 10px;
        }

        .preview-title {
            font-weight: 600;
            font-size: 1.2em;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .actions-group {
            display: flex;
            gap: 8px;
        }

        .btn-action {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 10px;
            padding: 8px 14px;
            color: var(--text-main);
            font-family: inherit;
            font-size: 0.9em;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s;
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .btn-action:hover {
            background: rgba(255, 255, 255, 0.1);
            border-color: rgba(255, 255, 255, 0.2);
        }

        .btn-action.download-highlight {
            background: var(--indigo-solid);
            border-color: var(--indigo-solid);
            color: white;
            box-shadow: 0 4px 10px rgba(99, 102, 241, 0.2);
        }

        .btn-action.download-highlight:hover {
            background: #4f46e5;
            box-shadow: 0 4px 14px rgba(99, 102, 241, 0.35);
        }

        /* Iframe Preview Panel */
        .preview-frame-container {
            flex-grow: 1;
            background: #ffffff;
            border-radius: 12px;
            overflow: hidden;
            position: relative;
            min-height: 400px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .preview-frame {
            width: 100%;
            height: 100%;
            border: none;
            background: #ffffff;
        }

        .preview-placeholder {
            text-align: center;
            color: var(--text-muted);
            padding: 40px;
        }

        .preview-placeholder svg {
            width: 64px;
            height: 64px;
            color: rgba(255, 255, 255, 0.15);
            margin-bottom: 12px;
        }

        /* Warnings & Logs */
        .notification {
            display: none;
            background: rgba(245, 158, 11, 0.1);
            border: 1px solid rgba(245, 158, 11, 0.2);
            color: #fbbf24;
            border-radius: 10px;
            padding: 12px 16px;
            font-size: 0.9em;
            margin-bottom: 15px;
            align-items: flex-start;
            gap: 10px;
        }

        .logs-collapsible {
            margin-top: 15px;
            border: 1px solid rgba(255, 255, 255, 0.05);
            border-radius: 10px;
            overflow: hidden;
        }

        .logs-header {
            background: rgba(255, 255, 255, 0.02);
            padding: 12px 16px;
            font-size: 0.85em;
            font-weight: 600;
            color: var(--text-muted);
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }

        .logs-header:hover {
            background: rgba(255, 255, 255, 0.05);
        }

        .logs-body {
            display: none;
            padding: 12px;
            background: #080c14;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.8em;
            color: #f87171;
            white-space: pre-wrap;
            max-height: 180px;
            overflow-y: auto;
            border-top: 1px solid rgba(255, 255, 255, 0.05);
        }

        /* Animations */
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(4px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .spin {
            animation: spin 1s linear infinite;
        }

        @keyframes spin {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
        }

        /* Floating notification toast */
        .toast {
            position: fixed;
            bottom: 24px;
            right: 24px;
            background: #1e293b;
            border: 1px solid rgba(255, 255, 255, 0.1);
            color: white;
            padding: 14px 20px;
            border-radius: 12px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.5);
            display: flex;
            align-items: center;
            gap: 10px;
            transform: translateY(100px);
            opacity: 0;
            transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
            z-index: 1000;
        }

        .toast.show {
            transform: translateY(0);
            opacity: 1;
        }
    </style>
</head>
<body>

    <header>
        <h1>LaTeX ➜ HTML Converter</h1>
        <p>Convierte tus proyectos LaTeX (.zip) en hermosas y responsivas páginas web con renderizado automático de fórmulas (MathJax) y layouts limpios.</p>
    </header>

    <div class="container">
        <!-- Control Panel Card -->
        <div class="card">
            <!-- Dropzone -->
            <div class="dropzone" id="dropzone">
                <svg fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                  <path d="M12 16.5V9.75m0 0l3 3m-3-3l-3 3M6.75 19.5a4.5 4.5 0 01-1.41-8.775 5.25 5.25 0 0110.233-2.33 3 3 0 013.758 3.848A3.752 3.752 0 0118 19.5H6.75z" stroke-linecap="round" stroke-linejoin="round"></path>
                </svg>
                <h3>Arrastra tu archivo .zip</h3>
                <p style="font-size: 0.85em; color: var(--text-muted); margin-top: 5px;">o haz clic para explorar en tu equipo</p>
                <input type="file" id="zip_input" accept=".zip">
            </div>

            <!-- File details -->
            <div class="file-info" id="file_info">
                <svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                  <path d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" stroke-linecap="round" stroke-linejoin="round"></path>
                </svg>
                <span class="file-info-text" id="file_name">documento.zip</span>
                <span class="file-clear" id="file_clear" title="Quitar archivo">
                    <svg style="width: 16px; height: 16px;" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                      <path d="M6 18L18 6M6 6l12 12" stroke-linecap="round" stroke-linejoin="round"></path>
                    </svg>
                </span>
            </div>

            <!-- Settings -->
            <div class="setting-group" style="margin-top: 20px;">
                <label class="setting-label">Tema de Diseño</label>
                <div class="themes-grid">
                    <button class="theme-btn active" data-theme="academic">Académico</button>
                    <button class="theme-btn" data-theme="minimalist">Moderno</button>
                    <button class="theme-btn" data-theme="dark">Oscuro</button>
                    <button class="theme-btn" data-theme="sepia">Sepia</button>
                    <button class="theme-btn" data-theme="transparent">Sin Fondo</button>
                </div>
            </div>

            <div class="setting-group">
                <label class="setting-label">Opciones del Documento</label>
                
                <div class="toggle-row">
                    <div class="toggle-info">
                        <span class="toggle-title">Índice de Contenido</span>
                        <span class="toggle-desc">Generar índice (TOC) automático</span>
                    </div>
                    <label class="switch">
                        <input type="checkbox" id="opt_toc" checked>
                        <span class="slider"></span>
                    </label>
                </div>

                <div class="toggle-row">
                    <div class="toggle-info">
                        <span class="toggle-title">Numerar Ecuaciones</span>
                        <span class="toggle-desc">Aplica numeración estilo AMS</span>
                    </div>
                    <label class="switch">
                        <input type="checkbox" id="opt_equations" checked>
                        <span class="slider"></span>
                    </label>
                </div>

                <div class="toggle-row">
                    <div class="toggle-info">
                        <span class="toggle-title">Habilitar Ecuaciones</span>
                        <span class="toggle-desc">Renderizar matemáticas MathJax</span>
                    </div>
                    <label class="switch">
                        <input type="checkbox" id="opt_mathjax" checked>
                        <span class="slider"></span>
                    </label>
                </div>
            </div>

            <div class="setting-group">
                <label class="setting-label">Portada del Libro (Imagen)</label>
                <div class="drop-zone" id="cover_dropzone" style="border: 2px dashed rgba(255,255,255,0.2); padding: 15px; border-radius: 8px; text-align: center; cursor: pointer; background: rgba(255,255,255,0.05); margin-top: 5px; transition: border-color 0.2s;">
                    <div style="font-size: 0.9em; color: #a5b4fc;" id="cover_status">Arrastra una imagen o haz clic para subir</div>
                    <input type="file" id="cover_input" accept="image/*" style="display: none;">
                </div>
                <div class="file-info" id="cover_file_info" style="display: none; margin-top: 8px;">
                    <svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" style="width: 16px; height: 16px; color: #a5b4fc; margin-right: 6px;">
                      <path d="M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159m-1.5-1.5l1.409-1.409a2.25 2.25 0 013.182 0l2.909 2.909m-18 3.75h16.5a1.5 1.5 0 001.5-1.5V6a1.5 1.5 0 00-1.5-1.5H3.75A1.5 1.5 0 002.25 6v12a1.5 1.5 0 001.5 1.5zm10.5-11.25h.008v.008h-.008V8.25zm.375 0a.375.375 0 11-.75 0 .375.375 0 01.75 0z" stroke-linecap="round" stroke-linejoin="round"></path>
                    </svg>
                    <span class="file-info-text" id="cover_filename" style="font-size: 0.85em; color: #cbd5e1;">cover.png</span>
                    <span class="file-clear" id="cover_clear" title="Quitar portada">
                        <svg style="width: 14px; height: 14px;" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                          <path d="M6 18L18 6M6 6l12 12" stroke-linecap="round" stroke-linejoin="round"></path>
                        </svg>
                    </span>
                </div>
            </div>

            <div class="setting-group">
                <label class="setting-label">Páginas Preliminares y Metadatos (Opcional)</label>
                
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 10px;">
                    <div style="display: flex; flex-direction: column; gap: 4px;">
                        <span style="font-size: 0.8em; color: #94a3b8;">Título</span>
                        <input type="text" id="book_title" class="format-select" style="text-align: left; padding: 8px 12px; height: 38px; border-radius: 6px;" placeholder="Título del libro">
                    </div>
                    <div style="display: flex; flex-direction: column; gap: 4px;">
                        <span style="font-size: 0.8em; color: #94a3b8;">Autor</span>
                        <input type="text" id="book_author" class="format-select" style="text-align: left; padding: 8px 12px; height: 38px; border-radius: 6px;" placeholder="Autor">
                    </div>
                </div>

                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 10px;">
                    <div style="display: flex; flex-direction: column; gap: 4px;">
                        <span style="font-size: 0.8em; color: #94a3b8;">Editorial</span>
                        <input type="text" id="book_publisher" class="format-select" style="text-align: left; padding: 8px 12px; height: 38px; border-radius: 6px;" placeholder="Editorial">
                    </div>
                    <div style="display: flex; flex-direction: column; gap: 4px;">
                        <span style="font-size: 0.8em; color: #94a3b8;">Idioma</span>
                        <input type="text" id="book_lang" class="format-select" style="text-align: left; padding: 8px 12px; height: 38px; border-radius: 6px;" placeholder="es" value="es">
                    </div>
                </div>

                <div style="display: flex; flex-direction: column; gap: 4px; margin-top: 10px;">
                    <span style="font-size: 0.8em; color: #94a3b8;">Sinopsis / Descripción</span>
                    <textarea id="book_desc" class="format-select" style="text-align: left; padding: 8px 12px; height: 60px; border-radius: 6px; font-family: inherit; resize: vertical;" placeholder="Descripción..."></textarea>
                </div>

                <div style="display: flex; flex-direction: column; gap: 4px; margin-top: 10px;">
                    <span style="font-size: 0.8em; color: #94a3b8;">Copyright / Página de Derechos</span>
                    <textarea id="book_copyright" class="format-select" style="text-align: left; padding: 8px 12px; height: 60px; border-radius: 6px; font-family: inherit; resize: vertical;" placeholder="© 2026 Reservados todos los derechos..."></textarea>
                </div>

                <div style="display: flex; flex-direction: column; gap: 4px; margin-top: 10px;">
                    <span style="font-size: 0.8em; color: #94a3b8;">Dedicatoria</span>
                    <textarea id="book_dedication" class="format-select" style="text-align: left; padding: 8px 12px; height: 60px; border-radius: 6px; font-family: inherit; resize: vertical;" placeholder="Dedicatoria..."></textarea>
                </div>

                <div style="display: flex; flex-direction: column; gap: 4px; margin-top: 10px;">
                    <span style="font-size: 0.8em; color: #94a3b8;">Prefacio / Introducción</span>
                    <textarea id="book_preface" class="format-select" style="text-align: left; padding: 8px 12px; height: 80px; border-radius: 6px; font-family: inherit; resize: vertical;" placeholder="Prólogo o prefacio..."></textarea>
                </div>
            </div>

            <div class="setting-group">
                <label class="setting-label">Formato de Salida</label>
                <select class="format-select" id="opt_format">
                    <option value="single">HTML Único (Imágenes Embebidas)</option>
                    <option value="zip">Archivo ZIP (HTML + Archivos de Imagen)</option>
                </select>
            </div>

            <button class="btn-convert" id="btn_convert" disabled>
                <span>Convertir a HTML</span>
            </button>
        </div>

        <!-- Preview Card -->
        <div class="card preview-card">
            <div class="preview-header">
                <div class="preview-title">
                    <svg style="width: 22px; height: 22px; color: var(--indigo-solid);" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                      <path d="M2.036 12.322a1.012 1.012 0 010-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178z" stroke-linecap="round" stroke-linejoin="round"></path>
                      <path d="M15 12a3 3 0 11-6 0 3 3 0 01-6 0z" stroke-linecap="round" stroke-linejoin="round"></path>
                    </svg>
                    <span>Vista Previa del Documento</span>
                </div>
                <div class="actions-group" id="actions_group" style="display: none;">
                    <button class="btn-action" id="btn_open_tab">
                        <svg style="width: 16px; height: 16px;" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                          <path d="M13.5 6H5.25A2.25 2.25 0 003 8.25v10.5A2.25 2.25 0 005.25 21h10.5A2.25 2.25 0 0018 18.75V10.5m-10.5 6L21 3m0 0h-5.25M21 3v5.25" stroke-linecap="round" stroke-linejoin="round"></path>
                        </svg>
                        Abrir pestaña
                    </button>
                    <a class="btn-action download-highlight" id="btn_download" style="text-decoration: none; display: inline-flex; align-items: center; justify-content: center; gap: 8px;">
                        <svg style="width: 16px; height: 16px;" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                          <path d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3" stroke-linecap="round" stroke-linejoin="round"></path>
                        </svg>
                        Descargar
                    </a>
                </div>
            </div>

            <!-- PDF Warnings -->
            <div class="notification" id="pdf_warning">
                <svg style="width: 20px; height: 20px; flex-shrink: 0;" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                  <path d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" stroke-linecap="round" stroke-linejoin="round"></path>
                </svg>
                <span id="pdf_warning_text">Advertencia sobre recursos del PDF.</span>
            </div>

            <!-- Iframe window -->
            <div class="preview-frame-container">
                <div class="preview-placeholder" id="preview_placeholder">
                    <svg fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                      <path d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" stroke-linecap="round" stroke-linejoin="round"></path>
                    </svg>
                    <p>Sube un archivo y haz clic en "Convertir" para ver la previsualización interactiva aquí.</p>
                </div>
                <iframe class="preview-frame" id="preview_frame" style="display: none;"></iframe>
            </div>

            <!-- Logs / Errores collapsible -->
            <div class="logs-collapsible" id="logs_container" style="display: none;">
                <div class="logs-header" id="logs_header">
                    <span>Registro de Compilación (Pandoc)</span>
                    <svg style="width: 16px; height: 16px;" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                      <path d="M19.5 8.25l-7.5 7.5-7.5-7.5" stroke-linecap="round" stroke-linejoin="round"></path>
                    </svg>
                </div>
                <div class="logs-body" id="logs_body"></div>
            </div>
        </div>
    </div>

    <!-- Floating toast -->
    <div class="toast" id="toast">
        <span id="toast_msg">Acción completada</span>
    </div>

    <script>
        // State
        let uploadedZipBase64 = '';
        let uploadedFilename = '';
        let currentTheme = 'academic';
        let convertedFileData = ''; // Base64 of converted file
        let convertedFilename = '';
        let convertedMimeType = '';
        let previewHtmlUrl = ''; // Blob URL for preview

        // DOM elements
        const dropzone = document.getElementById('dropzone');
        const zipInput = document.getElementById('zip_input');
        const fileInfo = document.getElementById('file_info');
        const fileName = document.getElementById('file_name');
        const fileClear = document.getElementById('file_clear');
        const btnConvert = document.getElementById('btn_convert');
        const btnDownload = document.getElementById('btn_download');
        const btnOpenTab = document.getElementById('btn_open_tab');
        const previewPlaceholder = document.getElementById('preview_placeholder');
        const previewFrame = document.getElementById('preview_frame');
        const actionsGroup = document.getElementById('actions_group');
        const pdfWarning = document.getElementById('pdf_warning');
        const pdfWarningText = document.getElementById('pdf_warning_text');
        const logsContainer = document.getElementById('logs_container');
        const logsHeader = document.getElementById('logs_header');
        const logsBody = document.getElementById('logs_body');
        const toast = document.getElementById('toast');

        // Theme selector handles
        document.querySelectorAll('.theme-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.theme-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                currentTheme = btn.dataset.theme;
            });
        });

        // Drag and drop event handlers
        ['dragenter', 'dragover'].forEach(eventName => {
            dropzone.addEventListener(eventName, (e) => {
                e.preventDefault();
                dropzone.classList.add('dragover');
            }, false);
        });

        ['dragleave', 'drop'].forEach(eventName => {
            dropzone.addEventListener(eventName, (e) => {
                e.preventDefault();
                dropzone.classList.remove('dragover');
            }, false);
        });

        dropzone.addEventListener('drop', (e) => {
            const dt = e.dataTransfer;
            const files = dt.files;
            if (files.length > 0) {
                handleFile(files[0]);
            }
        });

        zipInput.addEventListener('change', (e) => {
            if (zipInput.files.length > 0) {
                handleFile(zipInput.files[0]);
            }
        });

        fileClear.addEventListener('click', () => {
            clearFile();
        });

        // Collapsible logs
        logsHeader.addEventListener('click', () => {
            const isVisible = logsBody.style.display === 'block';
            logsBody.style.display = isVisible ? 'none' : 'block';
            const svg = logsHeader.querySelector('svg');
            svg.style.transform = isVisible ? 'rotate(0deg)' : 'rotate(180deg)';
        });

        function showToast(msg) {
            document.getElementById('toast_msg').innerText = msg;
            toast.classList.add('show');
            setTimeout(() => {
                toast.classList.remove('show');
            }, 3000);
        }

        function handleFile(file) {
            if (!file.name.endsWith('.zip')) {
                showToast('Por favor, selecciona un archivo .zip');
                return;
            }

            uploadedFilename = file.name;
            const reader = new FileReader();
            reader.readAsDataURL(file);
            reader.onload = function () {
                // Convert DataURL to plain Base64
                uploadedZipBase64 = reader.result.split(',')[1];
                
                // Update UI
                fileName.innerText = `${file.name} (${formatBytes(file.size)})`;
                fileInfo.style.display = 'flex';
                dropzone.style.display = 'none';
                btnConvert.disabled = false;
                showToast('Archivo ZIP cargado correctamente.');
            };
            reader.onerror = function (error) {
                showToast('Error al leer el archivo ZIP.');
                console.error(error);
            };
        }

        let coverBase64 = ''; // Base64 of cover image

        // Cover DOM elements
        const coverDropzone = document.getElementById('cover_dropzone');
        const coverInput = document.getElementById('cover_input');
        const coverFileInfo = document.getElementById('cover_file_info');
        const coverFilename = document.getElementById('cover_filename');
        const coverClear = document.getElementById('cover_clear');

        if (coverDropzone && coverInput) {
            coverDropzone.addEventListener('click', () => coverInput.click());

            ['dragenter', 'dragover'].forEach(eventName => {
                coverDropzone.addEventListener(eventName, (e) => {
                    e.preventDefault();
                    coverDropzone.style.borderColor = '#a5b4fc';
                    coverDropzone.style.background = 'rgba(165,180,252,0.1)';
                }, false);
            });

            ['dragleave', 'drop'].forEach(eventName => {
                coverDropzone.addEventListener(eventName, (e) => {
                    e.preventDefault();
                    coverDropzone.style.borderColor = 'rgba(255,255,255,0.2)';
                    coverDropzone.style.background = 'rgba(255,255,255,0.05)';
                }, false);
            });

            coverDropzone.addEventListener('drop', (e) => {
                const files = e.dataTransfer.files;
                if (files.length > 0) {
                    handleCoverFile(files[0]);
                }
            });

            coverInput.addEventListener('change', (e) => {
                if (coverInput.files.length > 0) {
                    handleCoverFile(coverInput.files[0]);
                }
            });

            coverClear.addEventListener('click', (e) => {
                e.stopPropagation();
                clearCover();
            });
        }

        function handleCoverFile(file) {
            if (!file.type.startsWith('image/')) {
                showToast('Por favor, selecciona una imagen para la portada.');
                return;
            }
            const reader = new FileReader();
            reader.readAsDataURL(file);
            reader.onload = function() {
                coverBase64 = reader.result.split(',')[1];
                coverFilename.innerText = `${file.name} (${formatBytes(file.size)})`;
                coverFileInfo.style.display = 'flex';
                coverDropzone.style.display = 'none';
            };
        }

        function clearCover() {
            coverBase64 = '';
            coverInput.value = '';
            coverFileInfo.style.display = 'none';
            coverDropzone.style.display = 'block';
        }

        function clearFile() {
            uploadedZipBase64 = '';
            uploadedFilename = '';
            zipInput.value = '';
            fileInfo.style.display = 'none';
            dropzone.style.display = 'block';
            btnConvert.disabled = true;
            btnConvert.innerHTML = '<span>Convertir a HTML</span>';
            clearCover();
            resetPreview();
        }

        function resetPreview() {
            previewPlaceholder.style.display = 'flex';
            previewFrame.style.display = 'none';
            previewFrame.src = '';
            actionsGroup.style.display = 'none';
            pdfWarning.style.display = 'none';
            logsContainer.style.display = 'none';
            logsBody.innerText = '';
            if (previewHtmlUrl) {
                URL.revokeObjectURL(previewHtmlUrl);
                previewHtmlUrl = '';
            }
            convertedFileData = '';
            convertedFilename = '';
            convertedMimeType = '';
        }

        function formatBytes(bytes) {
            if (bytes === 0) return '0 Bytes';
            const k = 1024;
            const sizes = ['Bytes', 'KB', 'MB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
        }

        // POST compilation request
        btnConvert.addEventListener('click', async () => {
            if (!uploadedZipBase64) return;

            btnConvert.disabled = true;
            btnConvert.innerHTML = `
                <svg class="spin" style="width: 20px; height: 20px;" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99"></path>
                </svg>
                <span>Convirtiendo...</span>
            `;

            resetPreview();

            const settings = {
                theme: currentTheme,
                toc: document.getElementById('opt_toc').checked,
                equations: document.getElementById('opt_equations').checked,
                mathjax: document.getElementById('opt_mathjax').checked,
                format: document.getElementById('opt_format').value,
                title: document.getElementById('book_title').value.trim(),
                author: document.getElementById('book_author').value.trim(),
                publisher: document.getElementById('book_publisher').value.trim(),
                lang: document.getElementById('book_lang').value.trim(),
                description: document.getElementById('book_desc').value.trim(),
                copyright: document.getElementById('book_copyright').value.trim(),
                dedication: document.getElementById('book_dedication').value.trim(),
                preface: document.getElementById('book_preface').value.trim()
            };

            try {
                const response = await fetch('/convert', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        zip_file: uploadedZipBase64,
                        cover_file: coverBase64,
                        settings: settings
                    })
                });

                const data = await response.json();
                
                if (!response.ok || !data.success) {
                    throw new Error(data.error || 'Ocurrió un error inesperado al procesar.');
                }

                showToast(data.saved_local_path ? '¡Guardado en descargas!' : 'Conversión exitosa!');
                
                // Save converted response
                convertedFileData = data.file_data;
                convertedFilename = data.filename;
                convertedMimeType = data.mime_type;

                // Setup Preview
                let previewBlob;
                if (data.mime_type === "application/zip") {
                    // In ZIP mode, we can't preview a raw ZIP in an iframe directly.
                    // However, we send a notification and render a success screen.
                    const zipPreviewHtml = `
                    <html>
                    <head>
                        <style>
                            body { font-family: system-ui, sans-serif; display: flex; flex-direction: column; align-items: center; justify-content: center; height: 90vh; color: #475569; text-align: center; background: #f8fafc; padding: 20px; }
                            h2 { color: #0f172a; margin-bottom: 10px; }
                            p { max-width: 500px; line-height: 1.5; margin-bottom: 20px; }
                            .zip-icon { font-size: 64px; margin-bottom: 16px; }
                            .download-btn { background: #6366f1; color: white; border: none; padding: 12px 24px; border-radius: 8px; font-weight: bold; cursor: pointer; text-decoration: none; box-shadow: 0 4px 10px rgba(99, 102, 241, 0.2); }
                            .download-btn:hover { background: #4f46e5; }
                        </style>
                    </head>
                    <body>
                        <div class="zip-icon">📦</div>
                        <h2>Paquete ZIP Generado Exitosamente</h2>
                        <p>Tu proyecto se ha compilado a HTML y se ha empaquetado junto a sus recursos de imágenes en el archivo <strong>${convertedFilename}</strong>.</p>
                        <a href="javascript:parent.downloadFile()" class="download-btn">Descargar ZIP ahora</a>
                    </body>
                    </html>
                    `;
                    previewBlob = new Blob([zipPreviewHtml], { type: 'text/html' });
                } else {
                    // HTML Mode
                    const binaryString = atob(convertedFileData);
                    const len = binaryString.length;
                    const bytes = new Uint8Array(len);
                    for (let i = 0; i < len; i++) {
                        bytes[i] = binaryString.charCodeAt(i);
                    }
                    previewBlob = new Blob([bytes], { type: 'text/html;charset=utf-8' });
                }
                
                previewHtmlUrl = URL.createObjectURL(previewBlob);
                previewFrame.src = previewHtmlUrl;
                previewPlaceholder.style.display = 'none';
                previewFrame.style.display = 'block';
                actionsGroup.style.display = 'flex';

                // Pre-populate the direct download anchor URL for native browser saving
                const byteCharacters = atob(convertedFileData);
                const byteNumbers = new Array(byteCharacters.length);
                for (let i = 0; i < byteCharacters.length; i++) {
                    byteNumbers[i] = byteCharacters.charCodeAt(i);
                }
                const byteArray = new Uint8Array(byteNumbers);
                const downloadBlob = new Blob([byteArray], { type: convertedMimeType });
                const downloadBlobUrl = URL.createObjectURL(downloadBlob);
                
                btnDownload.href = downloadBlobUrl;
                btnDownload.download = convertedFilename;

                // Display warnings if any
                if (data.warning) {
                    pdfWarningText.innerText = data.warning;
                    pdfWarning.style.display = 'flex';
                }

                // Display compilation logs/warnings & local save path
                let logText = "";
                if (data.saved_local_path) {
                    logText += `[SISTEMA LOCAL] Archivo guardado automáticamente en tu carpeta de Descargas:\n👉 ${data.saved_local_path}\n\n`;
                }
                if (data.logs && data.logs.trim()) {
                    logText += data.logs;
                }
                if (logText.trim()) {
                    logsBody.innerText = logText;
                    logsContainer.style.display = 'block';
                }

            } catch (err) {
                console.error(err);
                showToast('Error en la conversión.');
                previewPlaceholder.style.display = 'none';
                
                // Show errors in preview pane as an error screen
                const errorHtml = `
                <html>
                <head>
                    <style>
                        body { font-family: system-ui, sans-serif; padding: 30px; background: #fff5f5; color: #c53030; }
                        h2 { border-bottom: 1px solid #feb2b2; padding-bottom: 10px; margin-top: 0; }
                        pre { background: #fff; border: 1px solid #fed7d7; padding: 15px; border-radius: 6px; overflow-x: auto; font-family: monospace; font-size: 0.9em; white-space: pre-wrap; }
                    </style>
                </head>
                <body>
                    <h2>Error de Compilación</h2>
                    <p>Ocurrió un error al intentar compilar tu proyecto de LaTeX:</p>
                    <pre>${err.message}</pre>
                </body>
                </html>
                `;
                const errorBlob = new Blob([errorHtml], { type: 'text/html' });
                previewHtmlUrl = URL.createObjectURL(errorBlob);
                previewFrame.src = previewHtmlUrl;
                previewFrame.style.display = 'block';
            } finally {
                btnConvert.disabled = false;
                btnConvert.innerHTML = '<span>Convertir a HTML</span>';
            }
        });

        // Download functionality
        window.downloadFile = function() {
            if (!convertedFileData) return;
            
            const byteCharacters = atob(convertedFileData);
            const byteNumbers = new Array(byteCharacters.length);
            for (let i = 0; i < byteCharacters.length; i++) {
                byteNumbers[i] = byteCharacters.charCodeAt(i);
            }
            const byteArray = new Uint8Array(byteNumbers);
            const blob = new Blob([byteArray], { type: convertedMimeType });
            
            const link = document.createElement('a');
            link.href = URL.createObjectURL(blob);
            link.download = convertedFilename;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            
            showToast('Archivo descargado con éxito.');
        }

        btnDownload.addEventListener('click', () => {
            window.downloadFile();
        });

        // Open in new tab
        btnOpenTab.addEventListener('click', () => {
            if (previewHtmlUrl) {
                window.open(previewHtmlUrl, '_blank');
            }
        });
    </script>
</body>
</html>
"""

# ----------------------------------------------------------------------
# Main Runner & Server Init
# ----------------------------------------------------------------------
def check_port(port):
    """Check if the port is available."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('localhost', port))
            return True
        except socket.error:
            return False

def find_available_port(start_port):
    """Scan ports starting from start_port to find a free one."""
    port = start_port
    while port < 65535:
        if check_port(port):
            return port
        port += 1
    return start_port

def run_server(server_port):
    """Start the HTTP server on the given port."""
    server_address = ('localhost', server_port)
    httpd = ThreadingHTTPServer(server_address, RequestHandler)
    print(f"[SERVIDOR] Corriendo en http://localhost:{server_port}")
    print("[SERVIDOR] Presiona Ctrl+C en esta terminal para detenerlo.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
        print("\n[SERVIDOR] Detenido.")

def main():
    print("=====================================================")
    print("  Iniciando LaTeX a HTML Converter...")
    print("=====================================================")
    
    # 1. Check if pandoc is installed
    pandoc_path = get_pandoc_path()
    if not pandoc_path:
        print("[ERROR] Pandoc no está instalado o no se encuentra en el PATH.")
        print("Instálalo con Homebrew en Mac:")
        print("  brew install pandoc")
        print("O descárgalo desde la página oficial de Pandoc.")
        sys.exit(1)
        
    print(f"[INFO] Pandoc detectado en: {pandoc_path}")
    
    # 2. Find a free port
    port = find_available_port(DEFAULT_PORT)
    
    # 3. Open the browser automatically in a separate thread
    url = f"http://localhost:{port}"
    print(f"[INFO] Abriendo la aplicación en tu navegador: {url}")
    
    # Wait 1 second before opening browser to let the server startup
    def open_browser():
        webbrowser.open(url)
    threading.Timer(1.0, open_browser).start()
    
    # 4. Start the server
    run_server(port)

if __name__ == '__main__':
    main()
