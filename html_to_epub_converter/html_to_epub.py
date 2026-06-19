#!/usr/bin/env python3
import os
import sys
import re
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
import html
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn

# ----------------------------------------------------------------------
# Config & Paths
# ----------------------------------------------------------------------
DEFAULT_PORT = 8081

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

# ----------------------------------------------------------------------
# Custom CSS Stylesheets for the EPUB Book
# ----------------------------------------------------------------------
EPUB_THEMES = {
    'bookish': {
        'name': 'Bookish (Classic Serif)',
        'css': """/* Bookish - Classic Serif EPUB Theme */
body {
    font-family: "Georgia", "Times New Roman", Times, serif;
    line-height: 1.6;
    margin: 10%;
    color: #111111;
}
p {
    text-indent: 1.5em;
    margin-top: 0;
    margin-bottom: 0;
    text-align: justify;
}
p:first-of-type, h1 + p, h2 + p, h3 + p {
    text-indent: 0;
}
h1, h2, h3, h4 {
    font-family: "Georgia", serif;
    text-align: center;
    font-weight: bold;
    margin-top: 1.8em;
    margin-bottom: 0.8em;
}
h1 {
    font-size: 2.0em;
    page-break-before: always;
}
h2 {
    font-size: 1.6em;
}
h3 {
    font-size: 1.3em;
}
img {
    display: block;
    max-width: 100%;
    height: auto;
    margin: 1.5em auto;
}
blockquote {
    font-style: italic;
    margin: 1.5em 10%;
    line-height: 1.5;
    color: #444444;
}
table {
    margin: 2em auto;
    border-collapse: collapse;
    width: 90%;
}
th, td {
    border: 1px solid #cccccc;
    padding: 8px;
    text-align: left;
}
th {
    background-color: #f2f2f2;
}
"""
    },
    'modern': {
        'name': 'Modern (Clean Sans-Serif)',
        'css': """/* Modern - Clean Sans-Serif EPUB Theme */
body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
    line-height: 1.5;
    margin: 8%;
    color: #2b3a4a;
}
p {
    margin-top: 0.8em;
    margin-bottom: 0.8em;
    text-align: left;
}
h1, h2, h3, h4 {
    color: #0f172a;
    font-weight: 700;
    margin-top: 1.6em;
    margin-bottom: 0.6em;
}
h1 {
    font-size: 1.9em;
    border-bottom: 2px solid #e2e8f0;
    padding-bottom: 0.3em;
    page-break-before: always;
}
h2 {
    font-size: 1.5em;
    border-bottom: 1px solid #e2e8f0;
    padding-bottom: 0.2em;
}
h3 {
    font-size: 1.25em;
}
img {
    display: block;
    max-width: 100%;
    height: auto;
    margin: 2.0em auto;
    border-radius: 6px;
}
blockquote {
    border-left: 4px solid #3b82f6;
    background-color: #eff6ff;
    padding: 10px 15px;
    margin: 1.5em 0;
    border-radius: 0 6px 6px 0;
}
table {
    margin: 2em 0;
    border-collapse: collapse;
    width: 100%;
}
th, td {
    border-bottom: 1px solid #e2e8f0;
    padding: 10px;
    text-align: left;
}
th {
    background-color: #f8fafc;
    color: #0f172a;
}
"""
    },
    'academic': {
        'name': 'Academic (Formal Serif)',
        'css': """/* Academic - Formal Serif EPUB Theme */
body {
    font-family: "Times New Roman", Times, "Liberation Serif", serif;
    line-height: 1.5;
    margin: 12%;
    color: #000000;
}
p {
    text-align: justify;
    text-indent: 2.0em;
    margin: 0.4em 0;
}
p:first-of-type, h1 + p, h2 + p, h3 + p {
    text-indent: 0;
}
h1, h2, h3, h4 {
    font-family: "Times New Roman", serif;
    text-align: left;
    font-weight: bold;
    margin-top: 2.0em;
    margin-bottom: 0.8em;
}
h1 {
    font-size: 1.8em;
    text-align: center;
    page-break-before: always;
}
h2 {
    font-size: 1.4em;
    border-bottom: 1px solid #000000;
    padding-bottom: 0.2em;
}
h3 {
    font-size: 1.2em;
    font-style: italic;
}
img {
    display: block;
    max-width: 100%;
    height: auto;
    margin: 2.0em auto;
}
blockquote {
    margin: 1.5em 12%;
    text-align: justify;
    font-size: 0.95em;
}
table {
    margin: 2em auto;
    border-collapse: collapse;
    width: 100%;
    border-top: 2px solid #000000;
    border-bottom: 2px solid #000000;
}
th, td {
    padding: 8px;
    text-align: left;
}
th {
    border-bottom: 1px solid #000000;
    font-weight: bold;
}
"""
    }
}

from urllib.parse import unquote
import requests

def preprocess_html_images(html_dir):
    """
    Scans all HTML files in html_dir, finds img/embed tags, and:
    1. Decodes and cleans relative/local image paths.
    2. Renames the physical files on disk to match the clean paths.
    3. Extracts and decodes base64 data URIs into physical files.
    """
    images_dir = os.path.join(html_dir, 'images')
    os.makedirs(images_dir, exist_ok=True)
    
    base64_counter = 0

    for root, _, files in os.walk(html_dir):
        for file in files:
            if file.lower().endswith(('.html', '.htm')):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        html_content = f.read()
                    
                    modified = False
                    src_pattern = re.compile(r'(<(?:img|embed)\b[^>]*\bsrc=["\'])([^"\']*)(["\'][^>]*>)', re.IGNORECASE)
                    
                    def replacer(match):
                        nonlocal modified, base64_counter
                        prefix = match.group(1)
                        src = match.group(2)
                        suffix = match.group(3)
                        
                        if not src:
                            return match.group(0)
                        
                        if src.startswith('data:'):
                            try:
                                header, data_b64 = src.split(',', 1)
                                mime_type = header.split(';')[0].split(':')[1]
                                ext = mimetypes.guess_extension(mime_type) or '.png'
                                
                                img_data = base64.b64decode(data_b64)
                                base64_counter += 1
                                local_filename = f"extracted_b64_{base64_counter}{ext}"
                                local_path = os.path.join(images_dir, local_filename)
                                
                                with open(local_path, 'wb') as img_f:
                                    img_f.write(img_data)
                                
                                modified = True
                                print(f"[PREPROCESS] Extracted base64 image to images/{local_filename}")
                                return f"{prefix}images/{local_filename}{suffix}"
                            except Exception as b64_err:
                                print(f"[WARNING] Failed to extract base64 image: {b64_err}")
                                return match.group(0)
                                
                        if src.startswith(('http://', 'https://')):
                            return match.group(0)
                            
                        # Relative path
                        decoded_src = unquote(src)
                        decoded_src = decoded_src.replace('\\', '/')
                        
                        # Find physical path
                        physical_path = os.path.abspath(os.path.join(html_dir, decoded_src))
                        if not os.path.exists(physical_path):
                            physical_path = os.path.abspath(os.path.join(root, decoded_src))
                            
                        if os.path.exists(physical_path) and os.path.isfile(physical_path):
                            base_name = os.path.basename(physical_path)
                            parent_dir_name = os.path.basename(os.path.dirname(physical_path))
                            
                            clean_base = re.sub(r'[^a-zA-Z0-9_.]', '_', base_name)
                            clean_parent = re.sub(r'[^a-zA-Z0-9_.]', '_', parent_dir_name)
                            
                            clean_filename = f"{clean_parent}_{clean_base}"
                            if clean_parent == "images" or not clean_parent:
                                clean_filename = clean_base
                                
                            clean_local_path = os.path.join(images_dir, clean_filename)
                            
                            try:
                                if physical_path != clean_local_path:
                                    shutil.copy2(physical_path, clean_local_path)
                                modified = True
                                print(f"[PREPROCESS] Localized {decoded_src} to images/{clean_filename}")
                                return f"{prefix}images/{clean_filename}{suffix}"
                            except Exception as copy_err:
                                print(f"[WARNING] Failed to copy image {physical_path} to {clean_local_path}: {copy_err}")
                                return match.group(0)
                        else:
                            print(f"[WARNING] Image path not found on disk: {decoded_src} (checked {physical_path})")
                            return match.group(0)
                            
                    new_content = src_pattern.sub(replacer, html_content)
                    if modified:
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(new_content)
                except Exception as file_err:
                    print(f"[WARNING] Error pre-processing images in {file_path}: {file_err}")

def rebuild_epub(epub_path, source_dir):
    temp_epub_path = epub_path + '.tmp'
    try:
        with zipfile.ZipFile(temp_epub_path, 'w') as z:
            mimetype_path = os.path.join(source_dir, 'mimetype')
            if os.path.exists(mimetype_path):
                z.write(mimetype_path, 'mimetype', compress_type=zipfile.ZIP_STORED)
                
            for root, _, files in os.walk(source_dir):
                for file in files:
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, source_dir)
                    if rel_path == 'mimetype':
                        continue
                    if file.startswith('.') or 'desktop.ini' in file.lower():
                        continue
                    z.write(full_path, rel_path, compress_type=zipfile.ZIP_DEFLATED)
        shutil.move(temp_epub_path, epub_path)
    except Exception as rebuild_err:
        print(f"[POSTPROCESS] [ERROR] Failed to rebuild EPUB zip: {rebuild_err}")

def clean_nav_xhtml(content):
    def replacer(match):
        a_open = match.group(1)
        inner = match.group(2)
        a_close = match.group(3)
        temp = inner
        img_pattern = re.compile(r'<img[^>]*alt=[\"\']([^\"\']*)[\"\'][^>]*>')
        temp = img_pattern.sub(r' \1 ', temp)
        temp = re.sub(r'<[^>]+>', '', temp)
        temp = re.sub(r'\s+', ' ', temp).strip()
        return f'{a_open}{temp}{a_close}'
    a_pattern = re.compile(r'(<a\b[^>]*>)(.*?)(</a>)', re.DOTALL | re.IGNORECASE)
    return a_pattern.sub(replacer, content)

def postprocess_generated_epub(epub_path):
    print("[POSTPROCESS] Starting post-processing of EPUB...")
    
    with tempfile.TemporaryDirectory() as post_temp:
        try:
            with zipfile.ZipFile(epub_path, 'r') as z:
                z.extractall(post_temp)
        except Exception as unzip_err:
            print(f"[POSTPROCESS] Failed to unzip EPUB for post-processing: {unzip_err}")
            return
            
        modified = False
        
        # Clean nav.xhtml
        nav_file_path = None
        for root, _, files in os.walk(post_temp):
            for file in files:
                if file.endswith('nav.xhtml'):
                    nav_file_path = os.path.join(root, file)
                    break
            if nav_file_path:
                break
                
        if nav_file_path:
            try:
                with open(nav_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    nav_content = f.read()
                
                cleaned_nav = clean_nav_xhtml(nav_content)
                if cleaned_nav != nav_content:
                    with open(nav_file_path, 'w', encoding='utf-8') as f:
                        f.write(cleaned_nav)
                    modified = True
                    print("[POSTPROCESS] Cleaned nav.xhtml navigation list.")
            except Exception as nav_err:
                print(f"[POSTPROCESS] Failed to clean nav.xhtml: {nav_err}")
                
        # Locate content.opf
        opf_file_path = None
        for root, _, files in os.walk(post_temp):
            for file in files:
                if file.endswith('.opf'):
                    opf_file_path = os.path.join(root, file)
                    break
            if opf_file_path:
                break
                
        if not opf_file_path:
            print("[POSTPROCESS] content.opf not found, skipping remote SVG localization.")
            if modified:
                rebuild_epub(epub_path, post_temp)
            return

        # Find all XHTML files
        content_files = []
        for root, _, files in os.walk(post_temp):
            for file in files:
                if file.lower().endswith(('.xhtml', '.html', '.htm')):
                    if 'nav.xhtml' not in file.lower():
                        content_files.append(os.path.join(root, file))

        # Media directory
        epub_media_dir = os.path.join(os.path.dirname(opf_file_path), 'media')
        os.makedirs(epub_media_dir, exist_ok=True)
        
        new_manifest_items = []
        downloaded_count = 0
        
        # Match img or embed with remote src (possibly prefixed by relative dots)
        remote_src_pattern = re.compile(
            r'(<(?:img|embed)\b[^>]*\bsrc=["\'])((\.\./)*https?://[^"\']*)(["\'][^>]*>)', 
            re.IGNORECASE
        )
        
        for c_file in content_files:
            try:
                with open(c_file, 'r', encoding='utf-8', errors='ignore') as f:
                    c_content = f.read()
                
                c_modified = False
                
                def remote_replacer(match):
                    nonlocal c_modified, downloaded_count, new_manifest_items, modified
                    tag_start = match.group(1)
                    full_src = match.group(2)
                    tag_end = match.group(4)
                    
                    url_start_idx = full_src.find('http')
                    if url_start_idx == -1:
                        return match.group(0)
                    remote_url = full_src[url_start_idx:]
                    
                    remote_url = html.unescape(remote_url)
                    
                    try:
                        print(f"[POSTPROCESS] Downloading remote resource: {remote_url}")
                        resp = requests.get(remote_url, timeout=30)
                        downloaded_count += 1
                        ext = '.svg'
                        content_type = resp.headers.get('content-type', '')
                        if 'png' in content_type:
                            ext = '.png'
                        elif 'jpeg' in content_type or 'jpg' in content_type:
                            ext = '.jpg'
                        elif 'gif' in content_type:
                            ext = '.gif'
                            
                        local_filename = f"custom_math_{downloaded_count}{ext}"
                        local_dest = os.path.join(epub_media_dir, local_filename)
                        
                        if resp.status_code == 200:
                            with open(local_dest, 'wb') as img_f:
                                img_f.write(resp.content)
                        else:
                            print(f"[POSTPROCESS] [WARNING] Remote download failed with code {resp.status_code}. Generating fallback SVG.")
                            ext = '.svg'
                            local_filename = f"custom_math_{downloaded_count}{ext}"
                            local_dest = os.path.join(epub_media_dir, local_filename)
                            
                            # Extract raw TeX from URL for the fallback display
                            raw_tex = ""
                            try:
                                import urllib.parse
                                parsed_url = urllib.parse.urlparse(remote_url)
                                query = parsed_url.query
                                if query:
                                    raw_tex = urllib.parse.unquote(query)
                                else:
                                    raw_tex = urllib.parse.unquote(parsed_url.path)
                            except:
                                raw_tex = remote_url
                                
                            raw_tex_truncated = raw_tex[:100] + ('...' if len(raw_tex) > 100 else '')
                            escaped_tex = html.escape(raw_tex_truncated)
                            
                            fallback_svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="600" height="40">
  <text x="10" y="25" font-family="monospace" font-size="12" fill="#ef4444">[Error al cargar fórmula: {escaped_tex}]</text>
</svg>"""
                            with open(local_dest, 'w', encoding='utf-8') as img_f:
                                img_f.write(fallback_svg)
                                
                        mime_type = "image/svg+xml"
                        if ext == '.png':
                            mime_type = "image/png"
                        elif ext in ('.jpg', '.jpeg'):
                            mime_type = "image/jpeg"
                        elif ext == '.gif':
                            mime_type = "image/gif"
                            
                        new_manifest_items.append({
                            "id": f"custom_math_{downloaded_count}",
                            "href": f"media/{local_filename}",
                            "media-type": mime_type
                        })
                        
                        new_tag_start = tag_start
                        if '<embed' in tag_start.lower():
                            new_tag_start = tag_start.replace('<embed', '<img').replace('<EMBED', '<img')
                        
                        c_modified = True
                        modified = True
                        print(f"[POSTPROCESS] Localized {remote_url} to media/{local_filename}")
                        return f"{new_tag_start}../media/{local_filename}{tag_end}"
                    except Exception as download_err:
                        print(f"[POSTPROCESS] [WARNING] Failed to download {remote_url}: {download_err}. Generating fallback SVG.")
                        downloaded_count += 1
                        ext = '.svg'
                        local_filename = f"custom_math_{downloaded_count}{ext}"
                        local_dest = os.path.join(epub_media_dir, local_filename)
                        
                        escaped_tex = html.escape(remote_url[:100] + ('...' if len(remote_url) > 100 else ''))
                        fallback_svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="600" height="40">
  <text x="10" y="25" font-family="monospace" font-size="12" fill="#ef4444">[Error al descargar recurso: {escaped_tex}]</text>
</svg>"""
                        try:
                            with open(local_dest, 'w', encoding='utf-8') as img_f:
                                img_f.write(fallback_svg)
                            
                            mime_type = "image/svg+xml"
                            new_manifest_items.append({
                                "id": f"custom_math_{downloaded_count}",
                                "href": f"media/{local_filename}",
                                "media-type": mime_type
                            })
                            
                            new_tag_start = tag_start
                            if '<embed' in tag_start.lower():
                                new_tag_start = tag_start.replace('<embed', '<img').replace('<EMBED', '<img')
                            
                            c_modified = True
                            modified = True
                            return f"{new_tag_start}../media/{local_filename}{tag_end}"
                        except Exception as nested_err:
                            print(f"[POSTPROCESS] [ERROR] Failed to write fallback SVG: {nested_err}")
                            return match.group(0)
                        
                new_c_content = remote_src_pattern.sub(remote_replacer, c_content)
                if c_modified:
                    with open(c_file, 'w', encoding='utf-8') as f:
                        f.write(new_c_content)
            except Exception as content_err:
                print(f"[POSTPROCESS] Failed to parse content file {c_file}: {content_err}")
                
        # Register new items in content.opf manifest
        if new_manifest_items:
            try:
                with open(opf_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    opf_content = f.read()
                
                manifest_close_idx = opf_content.find('</manifest>')
                if manifest_close_idx != -1:
                    manifest_xml_lines = []
                    for item in new_manifest_items:
                        manifest_xml_lines.append(
                            f'    <item id="{item["id"]}" href="{item["href"]}" media-type="{item["media-type"]}" />'
                        )
                    
                    insertion_str = '\n'.join(manifest_xml_lines) + '\n'
                    new_opf_content = (
                        opf_content[:manifest_close_idx] + 
                        insertion_str + 
                        opf_content[manifest_close_idx:]
                    )
                    
                    with open(opf_file_path, 'w', encoding='utf-8') as f:
                        f.write(new_opf_content)
                    print(f"[POSTPROCESS] Registered {len(new_manifest_items)} new assets in content.opf")
                    modified = True
            except Exception as opf_err:
                print(f"[POSTPROCESS] Failed to modify content.opf: {opf_err}")
                
        if modified:
            rebuild_epub(epub_path, post_temp)
            print("[POSTPROCESS] EPUB post-processing completed and package rebuilt.")
        else:
            print("[POSTPROCESS] No post-processing modifications required.")

# ----------------------------------------------------------------------
# Backend EPUB Conversion Logic
# ----------------------------------------------------------------------
def perform_epub_conversion(html_zip_bytes, cover_bytes, settings):
    """
    Extracts the source HTML or ZIP, writes YAML metadata and custom CSS,
    and runs Pandoc to generate a standard EPUB.
    """
    pandoc_path = get_pandoc_path()
    if not pandoc_path:
        return {
            "success": False,
            "error": "Pandoc was not found on your system. Please install it using: brew install pandoc"
        }

    # Extract configurations
    book_title = settings.get('title', 'Libro Sin Título').strip()
    book_author = settings.get('author', 'Autor Desconocido').strip()
    book_lang = settings.get('lang', 'es').strip()
    book_publisher = settings.get('publisher', '').strip()
    book_rights = settings.get('rights', '').strip()
    book_desc = settings.get('description', '').strip()
    book_copyright = settings.get('copyright', '').strip()
    book_dedication = settings.get('dedication', '').strip()
    book_preface = settings.get('preface', '').strip()
    
    theme_key = settings.get('theme', 'bookish')
    include_toc = settings.get('toc', True)
    toc_depth = settings.get('toc_depth', 3)
    chapter_level = settings.get('chapter_level', 2)
    math_rendering = settings.get('math_rendering', 'webtex_svg')

    theme_css = EPUB_THEMES.get(theme_key, EPUB_THEMES['bookish'])['css']

    with tempfile.TemporaryDirectory() as temp_dir:
        extract_dir = os.path.join(temp_dir, 'extracted')
        os.makedirs(extract_dir, exist_ok=True)

        # 1. Determine if input is a ZIP or a raw HTML file
        is_zip = False
        try:
            is_zip = zipfile.is_zipfile(io.BytesIO(html_zip_bytes))
        except:
            pass

        if is_zip:
            # Save and extract ZIP
            zip_path = os.path.join(temp_dir, 'input.zip')
            with open(zip_path, 'wb') as f:
                f.write(html_zip_bytes)
            try:
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_dir)
            except Exception as e:
                return {"success": False, "error": f"Failed to extract ZIP archive: {str(e)}"}
        else:
            # Treat as single HTML file
            html_path = os.path.join(extract_dir, 'index.html')
            try:
                with open(html_path, 'wb') as f:
                    f.write(html_zip_bytes)
            except Exception as e:
                return {"success": False, "error": f"Failed to save HTML source: {str(e)}"}

        # 2. Find the entry HTML file
        main_html = None
        
        # Search for index.html first (case-insensitive)
        for root, _, files in os.walk(extract_dir):
            for file in files:
                if file.lower() == 'index.html':
                    main_html = os.path.join(root, file)
                    break
            if main_html:
                break

        # Fallback to the first found .html file
        if not main_html:
            for root, _, files in os.walk(extract_dir):
                for file in files:
                    if file.lower().endswith(('.html', '.htm')):
                        main_html = os.path.join(root, file)
                        break
                if main_html:
                    break

        if not main_html:
            return {
                "success": False,
                "error": "Could not find a valid .html file inside the uploaded file. Please verify it contains at least one HTML page."
            }

        html_dir = os.path.dirname(main_html)

        # Pre-process image files (clean filenames, decode url-encoding, extract base64)
        preprocess_html_images(extract_dir)

        # Strip inline TOC from HTML files to prevent unresolved link errors (E24010) in EPUB
        for root, _, files in os.walk(extract_dir):
            for file in files:
                if file.lower().endswith(('.html', '.htm')):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            html_data = f.read()
                        
                        # Find and remove <nav id="TOC"...> or <div id="TOC"...>
                        toc_match = re.search(r'<(nav|div)\s+[^>]*id="TOC"[^>]*>', html_data, re.IGNORECASE)
                        if toc_match:
                            tag = toc_match.group(1)
                            open_tags = 1
                            pos = toc_match.end()
                            while open_tags > 0 and pos < len(html_data):
                                next_open = html_data.find(f'<{tag}', pos)
                                next_close = html_data.find(f'</{tag}>', pos)
                                if next_close == -1:
                                    break
                                if next_open != -1 and next_open < next_close:
                                    open_tags += 1
                                    pos = next_open + len(tag) + 1
                                else:
                                    open_tags -= 1
                                    pos = next_close + len(tag) + 3
                            html_data = html_data[:toc_match.start()] + html_data[pos:]
                            
                            with open(file_path, 'w', encoding='utf-8') as f:
                                f.write(html_data)
                            print(f"[EPUB] Stripped inline TOC from {file_path} to prevent E24010 errors.")
                    except Exception as strip_err:
                        print(f"[WARNING] Could not strip TOC from {file_path}: {strip_err}")
        
        # Helper to format multiline text into HTML paragraphs
        def format_text_to_html(text):
            if not text:
                return ""
            paragraphs = text.replace('\r\n', '\n').split('\n\n')
            html_paras = []
            for p in paragraphs:
                if p.strip():
                    lines = p.split('\n')
                    para_content = "<br/>".join(html.escape(line) for line in lines)
                    html_paras.append(f"<p>{para_content}</p>")
            return "\n".join(html_paras)

        has_copyright = False
        if book_copyright:
            copyright_html = format_text_to_html(book_copyright)
            copyright_content = f"""<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" lang="{book_lang}">
<head>
    <meta charset="UTF-8" />
    <title>Copyright</title>
    <link rel="stylesheet" href="epub.css" type="text/css" />
</head>
<body>
    <h1 style="display: none; visibility: hidden;">Copyright</h1>
    <section class="copyright-page" style="margin-top: 30%; text-align: center; font-size: 0.95em; line-height: 1.6; color: #374151;">
        {copyright_html}
    </section>
</body>
</html>"""
            try:
                with open(os.path.join(html_dir, '00_copyright.html'), 'w', encoding='utf-8') as f:
                    f.write(copyright_content)
                has_copyright = True
            except Exception as e:
                return {"success": False, "error": f"Failed to write Copyright page: {str(e)}"}

        has_dedication = False
        if book_dedication:
            dedication_html = format_text_to_html(book_dedication)
            dedication_content = f"""<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" lang="{book_lang}">
<head>
    <meta charset="UTF-8" />
    <title>Dedicatoria</title>
    <link rel="stylesheet" href="epub.css" type="text/css" />
</head>
<body>
    <h1 style="display: none; visibility: hidden;">Dedicatoria</h1>
    <section class="dedication-page" style="margin-top: 35%; text-align: center; font-style: italic; font-size: 1.1em; line-height: 1.6;">
        {dedication_html}
    </section>
</body>
</html>"""
            try:
                with open(os.path.join(html_dir, '00_dedication.html'), 'w', encoding='utf-8') as f:
                    f.write(dedication_content)
                has_dedication = True
            except Exception as e:
                return {"success": False, "error": f"Failed to write Dedication page: {str(e)}"}

        has_preface = False
        if book_preface:
            preface_html = format_text_to_html(book_preface)
            preface_content = f"""<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" lang="{book_lang}">
<head>
    <meta charset="UTF-8" />
    <title>Prefacio</title>
    <link rel="stylesheet" href="epub.css" type="text/css" />
</head>
<body>
    <section class="preface-page" style="padding: 5% 0; line-height: 1.6;">
        <h1 style="text-align: center; font-size: 1.8em; margin-bottom: 1.5em;">Prefacio</h1>
        <div class="preface-content" style="text-align: justify;">
            {preface_html}
        </div>
    </section>
</body>
</html>"""
            try:
                with open(os.path.join(html_dir, '00_preface.html'), 'w', encoding='utf-8') as f:
                    f.write(preface_content)
                has_preface = True
            except Exception as e:
                return {"success": False, "error": f"Failed to write Preface page: {str(e)}"}

        # 3. Create metadata.yaml inside html_dir
        metadata_path = os.path.join(html_dir, 'metadata.yaml')
        try:
            # We construct a formatted YAML block manually to escape multiline details properly
            yaml_lines = ["---", f'title: "{book_title}"', f'author: "{book_author}"', f'language: "{book_lang}"', 'toc-title: "Índice"']
            if book_publisher:
                yaml_lines.append(f'publisher: "{book_publisher}"')
            if book_rights:
                yaml_lines.append(f'rights: "{book_rights}"')
            if book_desc:
                # Use YAML block scalar for multiline descriptions
                yaml_lines.append('description: |')
                for line in book_desc.split('\n'):
                    yaml_lines.append(f'  {line}')
            yaml_lines.append("...")
            
            with open(metadata_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(yaml_lines) + '\n')
        except Exception as e:
            return {"success": False, "error": f"Failed to generate metadata block: {str(e)}"}

        # 4. Save custom CSS stylesheet
        css_path = os.path.join(html_dir, 'epub.css')
        try:
            with open(css_path, 'w', encoding='utf-8') as f:
                f.write(theme_css)
        except Exception as e:
            return {"success": False, "error": f"Failed to write CSS stylesheet: {str(e)}"}

        # 5. Handle Cover Image if uploaded
        cover_path = None
        if cover_bytes:
            # Try to guess mime type to use correct extension
            ext = '.png'
            try:
                # Simple magic number check for JPEG
                if cover_bytes.startswith(b'\xff\xd8\xff'):
                    ext = '.jpg'
            except:
                pass
            cover_path = os.path.join(html_dir, f'cover{ext}')
            try:
                with open(cover_path, 'wb') as f:
                    f.write(cover_bytes)
            except Exception as e:
                return {"success": False, "error": f"Failed to write Cover image: {str(e)}"}

        # 6. Build Pandoc Command
        out_epub_name = 'book.epub'
        out_epub_path = os.path.join(html_dir, out_epub_name)

        input_files = []
        if has_copyright:
            input_files.append('00_copyright.html')
        if has_dedication:
            input_files.append('00_dedication.html')
        if has_preface:
            input_files.append('00_preface.html')
        input_files.append(os.path.basename(main_html))

        pandoc_cmd = [
            pandoc_path
        ]
        pandoc_cmd.extend(input_files)
        pandoc_cmd.extend([
            '--from=html+tex_math_single_backslash+tex_math_double_backslash',
            '--to=epub3',
            '--metadata-file=metadata.yaml',
            '--css=epub.css',
            '--wrap=preserve',
            '--resource-path=.',
            '-o', out_epub_name
        ])

        if math_rendering == 'webtex_svg':
            pandoc_cmd.append('--webtex=https://latex.codecogs.com/svg.latex?')
        elif math_rendering == 'mathml':
            pandoc_cmd.append('--mathml')
        elif math_rendering == 'mathjax':
            pandoc_cmd.append('--mathjax')

        if cover_path:
            pandoc_cmd.append(f'--epub-cover-image={os.path.basename(cover_path)}')
        if include_toc:
            pandoc_cmd.append('--toc')
            pandoc_cmd.extend(['--toc-depth', str(toc_depth)])
        
        pandoc_cmd.extend(['--epub-chapter-level', str(chapter_level)])

        # 7. Run Pandoc
        try:
            result = subprocess.run(
                pandoc_cmd,
                cwd=html_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=300
            )
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "The compilation timed out (max 300s)."}
        except Exception as e:
            return {"success": False, "error": f"Error running Pandoc: {str(e)}"}

        if not os.path.exists(out_epub_path):
            return {
                "success": False,
                "error": f"Pandoc failed to generate EPUB file. Diagnostic details:\n{result.stderr}"
            }

        # Post-process generated EPUB (clean TOC, download failed SVGs, etc.)
        try:
            postprocess_generated_epub(out_epub_path)
        except Exception as post_err:
            print(f"[WARNING] EPUB post-processing failed: {post_err}")

        # 8. Encode and return output EPUB
        try:
            with open(out_epub_path, 'rb') as f:
                epub_bytes = f.read()
            b64_output = base64.b64encode(epub_bytes).decode('utf-8')
            
            clean_filename = "".join(c for c in book_title if c.isalnum() or c in (' ', '_', '-')).strip()
            clean_filename = clean_filename.replace(' ', '_')
            if not clean_filename:
                clean_filename = "ebook"
            clean_filename += ".epub"

            # Auto-save local copy directly to Downloads folder
            saved_local_path = None
            try:
                home_dir = os.path.expanduser('~')
                downloads_dir = os.path.join(home_dir, 'Downloads')
                if os.path.exists(downloads_dir):
                    target_path = os.path.join(downloads_dir, clean_filename)
                    with open(target_path, 'wb') as out_f:
                        out_f.write(epub_bytes)
                    saved_local_path = target_path
                    print(f"[SERVIDOR] EPUB guardado localmente en descargas: {target_path}")
            except Exception as save_err:
                print(f"[AVISO] No se pudo guardar la copia del EPUB en Downloads: {save_err}")

            return {
                "success": True,
                "filename": clean_filename,
                "file_data": b64_output,
                "mime_type": "application/epub+zip",
                "logs": result.stderr,
                "saved_local_path": saved_local_path
            }
        except Exception as e:
            return {"success": False, "error": f"Failed to encode generated EPUB: {str(e)}"}

# ----------------------------------------------------------------------
# Web Server Request Handler
# ----------------------------------------------------------------------
class RequestHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Mute standard HTTP request logs to keep stdout readable
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
                
                # Retrieve base64 files
                b64_zip = request_data.get('html_file', '')
                b64_cover = request_data.get('cover_file', '')
                settings = request_data.get('settings', {})
                
                if not b64_zip:
                    self.send_response(400)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({"success": False, "error": "No HTML or ZIP content provided"}).encode('utf-8'))
                    return
                
                # Decode bytes
                html_bytes = base64.b64decode(b64_zip)
                cover_bytes = base64.b64decode(b64_cover) if b64_cover else None
                
                # Convert
                response_data = perform_epub_conversion(html_bytes, cover_bytes, settings)
                
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
# Frontend HTML String (Dashboard UI)
# ----------------------------------------------------------------------
FRONTEND_HTML = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>HTML to EPUB Converter</title>
    <!-- Google Fonts -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-dark: #070a13;
            --card-bg: rgba(13, 19, 33, 0.75);
            --border-glow: rgba(99, 102, 241, 0.2);
            --accent-glow: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%);
            --accent-glow-hover: linear-gradient(135deg, #2563eb 0%, #7c3aed 100%);
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --blue-solid: #3b82f6;
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

        /* Ambient glow spots */
        body::before {
            content: '';
            position: absolute;
            width: 450px;
            height: 450px;
            background: rgba(59, 130, 246, 0.15);
            border-radius: 50%;
            filter: blur(90px);
            top: -120px;
            left: -120px;
            z-index: -1;
        }

        body::after {
            content: '';
            position: absolute;
            width: 450px;
            height: 450px;
            background: rgba(139, 92, 246, 0.12);
            border-radius: 50%;
            filter: blur(90px);
            bottom: -120px;
            right: -120px;
            z-index: -1;
        }

        header {
            margin-top: 40px;
            margin-bottom: 30px;
            text-align: center;
        }

        header h1 {
            font-size: 2.6em;
            font-weight: 700;
            background: linear-gradient(to right, #60a5fa, #a78bfa);
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
                grid-template-columns: 460px 1fr;
            }
        }

        .card {
            background: var(--card-bg);
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 20px;
            padding: 28px;
            box-shadow: 0 10px 30px 0 rgba(0, 0, 0, 0.4);
            display: flex;
            flex-direction: column;
            transition: all 0.3s ease;
        }

        .card:hover {
            border-color: rgba(59, 130, 246, 0.2);
            box-shadow: 0 10px 40px 0 rgba(59, 130, 246, 0.05);
        }

        .section-title {
            font-size: 1.25em;
            font-weight: 600;
            margin-bottom: 18px;
            color: #f1f5f9;
            border-bottom: 1px solid rgba(255,255,255,0.08);
            padding-bottom: 8px;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        /* Drag and Drop Zone */
        .dropzone-container {
            display: grid;
            grid-template-columns: 1fr;
            gap: 15px;
            margin-bottom: 24px;
        }

        @media (min-width: 400px) {
            .dropzone-container.split {
                grid-template-columns: 1fr 1fr;
            }
        }

        .dropzone {
            border: 2px dashed rgba(255, 255, 255, 0.15);
            border-radius: 14px;
            padding: 25px 15px;
            text-align: center;
            cursor: pointer;
            transition: all 0.2s ease;
            position: relative;
            background: rgba(255, 255, 255, 0.01);
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            min-height: 140px;
        }

        .dropzone:hover, .dropzone.dragover {
            border-color: var(--blue-solid);
            background: rgba(59, 130, 246, 0.06);
            box-shadow: 0 0 15px rgba(59, 130, 246, 0.1) inset;
        }

        .dropzone svg {
            width: 40px;
            height: 40px;
            margin-bottom: 8px;
            color: var(--text-muted);
            transition: all 0.2s ease;
        }

        .dropzone:hover svg, .dropzone.dragover svg {
            color: #60a5fa;
            transform: translateY(-2px);
        }

        .dropzone span {
            font-size: 0.9em;
            font-weight: 500;
        }

        .dropzone .small-hint {
            font-size: 0.75em;
            color: var(--text-muted);
            margin-top: 4px;
        }

        .dropzone input[type="file"] {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            opacity: 0;
            cursor: pointer;
            z-index: 2;
            font-size: 0; /* prevents tooltip on some browsers */
        }

        .file-info {
            display: none;
            align-items: center;
            gap: 8px;
            background: rgba(59, 130, 246, 0.1);
            border: 1px solid rgba(59, 130, 246, 0.3);
            border-radius: 8px;
            padding: 8px 12px;
            margin-top: -12px;
            margin-bottom: 20px;
            font-size: 0.85em;
            animation: fadeIn 0.3s ease;
        }

        .file-info svg {
            width: 16px;
            height: 16px;
            color: #4ade80;
            flex-shrink: 0;
        }

        .file-info-text {
            font-weight: 500;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .file-clear {
            cursor: pointer;
            color: var(--text-muted);
            margin-left: auto;
            display: flex;
            align-items: center;
        }

        .file-clear:hover {
            color: #f87171;
        }

        /* Config Form */
        .setting-group {
            margin-bottom: 18px;
        }

        .setting-group label {
            display: block;
            font-size: 0.9em;
            font-weight: 500;
            margin-bottom: 6px;
            color: #cbd5e1;
        }

        .input-text, .select-input, .textarea-input {
            width: 100%;
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 8px;
            padding: 10px 14px;
            color: var(--text-main);
            font-family: inherit;
            font-size: 0.9em;
            transition: all 0.2s ease;
        }

        .input-text:focus, .select-input:focus, .textarea-input:focus {
            outline: none;
            border-color: var(--blue-solid);
            background: rgba(255, 255, 255, 0.08);
            box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.15);
        }

        .textarea-input {
            resize: vertical;
            min-height: 80px;
        }

        .select-input option {
            background-color: var(--bg-dark);
            color: var(--text-main);
        }

        .row-grid {
            display: grid;
            grid-template-columns: 1fr;
            gap: 15px;
        }

        @media (min-width: 400px) {
            .row-grid {
                grid-template-columns: 1fr 1fr;
            }
        }

        .toggle-container {
            display: flex;
            align-items: center;
            gap: 10px;
            cursor: pointer;
            margin-top: 5px;
            user-select: none;
        }

        .toggle-switch {
            position: relative;
            width: 44px;
            height: 22px;
            background-color: rgba(255,255,255,0.15);
            border-radius: 11px;
            transition: background-color 0.2s;
        }

        .toggle-switch::after {
            content: '';
            position: absolute;
            width: 18px;
            height: 18px;
            border-radius: 50%;
            background-color: white;
            top: 2px;
            left: 2px;
            transition: transform 0.2s;
        }

        .toggle-checkbox {
            display: none;
        }

        .toggle-checkbox:checked + .toggle-switch {
            background: var(--accent-glow);
        }

        .toggle-checkbox:checked + .toggle-switch::after {
            transform: translateX(22px);
        }

        .toggle-label {
            font-size: 0.9em;
            color: #cbd5e1;
        }

        /* Convert Button */
        .convert-btn {
            background: var(--accent-glow);
            border: none;
            border-radius: 10px;
            color: white;
            font-size: 1em;
            font-weight: 600;
            padding: 14px;
            cursor: pointer;
            transition: all 0.2s ease;
            box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
            margin-top: 10px;
        }

        .convert-btn:hover:not(:disabled) {
            background: var(--accent-glow-hover);
            transform: translateY(-1px);
            box-shadow: 0 6px 16px rgba(59, 130, 246, 0.4);
        }

        .convert-btn:active:not(:disabled) {
            transform: translateY(1px);
        }

        .convert-btn:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            box-shadow: none;
        }

        /* Spinner */
        .spinner {
            display: none;
            width: 18px;
            height: 18px;
            border: 2.5px solid rgba(255,255,255,0.3);
            border-radius: 50%;
            border-top-color: white;
            animation: spin 0.8s linear infinite;
        }

        @keyframes spin {
            to { transform: rotate(360deg); }
        }

        /* Console */
        .console-container {
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 14px;
            overflow: hidden;
            margin-top: 24px;
            background: rgba(0, 0, 0, 0.4);
        }

        .console-header {
            background: rgba(255, 255, 255, 0.03);
            padding: 10px 16px;
            font-size: 0.85em;
            font-weight: 500;
            border-bottom: 1px solid rgba(255, 255, 255, 0.08);
            color: var(--text-muted);
            display: flex;
            align-items: center;
            justify-content: space-between;
            cursor: pointer;
            user-select: none;
        }

        .console-header:hover {
            background: rgba(255, 255, 255, 0.05);
            color: #cbd5e1;
        }

        .console-body {
            height: 120px;
            overflow-y: auto;
            padding: 12px 16px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.8em;
            color: #38bdf8;
            line-height: 1.5;
            white-space: pre-wrap;
            display: block;
        }

        /* Right Panel Preview / Success */
        .preview-card {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            min-height: 400px;
            text-align: center;
            padding: 40px;
        }

        .preview-placeholder svg {
            width: 72px;
            height: 72px;
            color: rgba(255,255,255,0.06);
            margin-bottom: 16px;
        }

        .preview-placeholder h3 {
            font-size: 1.25em;
            margin-bottom: 6px;
            color: var(--text-muted);
        }

        .preview-placeholder p {
            font-size: 0.9em;
            color: rgba(255,255,255,0.3);
            max-width: 320px;
        }

        /* Success State */
        .success-state {
            display: none;
            flex-direction: column;
            align-items: center;
            animation: fadeIn 0.5s ease;
        }

        .success-icon {
            font-size: 4em;
            margin-bottom: 20px;
            filter: drop-shadow(0 0 15px rgba(59, 130, 246, 0.3));
        }

        .success-title {
            font-size: 1.5em;
            font-weight: 600;
            margin-bottom: 10px;
            color: #f1f5f9;
        }

        .success-text {
            font-size: 0.95em;
            color: var(--text-muted);
            margin-bottom: 30px;
            max-width: 400px;
            line-height: 1.6;
        }

        .success-actions {
            display: flex;
            flex-direction: column;
            width: 100%;
            max-width: 280px;
            gap: 15px;
        }

        .download-btn {
            background: linear-gradient(135deg, #10b981 0%, #059669 100%);
            border: none;
            border-radius: 10px;
            color: white;
            font-size: 1em;
            font-weight: 600;
            padding: 14px;
            cursor: pointer;
            text-decoration: none;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
            box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
            transition: all 0.2s ease;
        }

        .download-btn:hover {
            background: linear-gradient(135deg, #059669 0%, #047857 100%);
            transform: translateY(-1px);
            box-shadow: 0 6px 16px rgba(16, 185, 129, 0.4);
        }

        .download-btn:active {
            transform: translateY(1px);
        }

        .reset-btn {
            background: transparent;
            border: 1px solid rgba(255, 255, 255, 0.15);
            border-radius: 10px;
            color: var(--text-main);
            font-size: 0.9em;
            font-weight: 500;
            padding: 10px;
            cursor: pointer;
            transition: all 0.2s ease;
        }

        .reset-btn:hover {
            background: rgba(255,255,255,0.05);
            border-color: rgba(255,255,255,0.3);
        }

        /* Animations */
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }

        /* Toast Notification */
        .toast {
            position: fixed;
            bottom: 24px;
            right: 24px;
            background: #ef4444;
            color: white;
            padding: 12px 20px;
            border-radius: 8px;
            font-size: 0.9em;
            font-weight: 500;
            box-shadow: 0 10px 25px rgba(0,0,0,0.3);
            display: none;
            z-index: 100;
            animation: slideUp 0.3s ease;
        }

        @keyframes slideUp {
            from { transform: translateY(100px); opacity: 0; }
            to { transform: translateY(0); opacity: 1; }
        }
    </style>
</head>
<body>

    <header>
        <h1>HTML to EPUB Converter</h1>
        <p>Convierte tus proyectos o archivos HTML en libros electrónicos estándar EPUB 3 con metadatos y portadas personalizadas.</p>
    </header>

    <div class="container">
        
        <!-- Left configuration panel -->
        <div class="card">
            <div class="section-title">
                <svg width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"></path></svg>
                Archivos del Libro
            </div>

            <div class="dropzone-container split">     
                <!-- HTML or ZIP dropzone -->
                <label class="dropzone" id="html-dropzone">
                    <svg fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m.75 12l3 3m0 0l3-3m-3 3v-6m-1.5-9H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z"></path></svg>
                    <span>Proyecto HTML</span>
                    <span class="small-hint">.html o .zip</span>
                    <input type="file" id="html-file-input" accept=".html,.htm,.zip" style="position:absolute; top:0; left:0; width:100%; height:100%; opacity:0; cursor:pointer; z-index:2;">
                </label>

                <!-- Cover image dropzone -->
                <label class="dropzone" id="cover-dropzone">
                    <svg fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="m2.25 15.75 5.159-5.159a2.25 2.25 0 0 1 3.182 0l5.159 5.159m-1.5-1.5 1.409-1.409a2.25 2.25 0 0 1 3.182 0l2.909 2.909m-18 3.75h16.5a1.5 1.5 0 0 0 1.5-1.5V6a1.5 1.5 0 0 0-1.5-1.5H3.75A1.5 1.5 0 0 0 2.25 6v12a1.5 1.5 0 0 0 1.5 1.5Zm10.5-11.25h.008v.008h-.008V8.25Zm.375 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Z"></path></svg>
                    <span>Portada</span>
                    <span class="small-hint">PNG o JPG (opcional)</span>
                    <input type="file" id="cover-file-input" accept=".png,.jpg,.jpeg" style="position:absolute; top:0; left:0; width:100%; height:100%; opacity:0; cursor:pointer; z-index:2;">
                </label>
            </div>

            <!-- Upload file indicators -->
            <div class="file-info" id="html-file-info">
                <svg fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"></path></svg>
                <span class="file-info-text" id="html-filename">documento.html</span>
                <span class="file-clear" onclick="clearHtmlFile()">✕</span>
            </div>
            <div class="file-info" id="cover-file-info">
                <svg fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"></path></svg>
                <span class="file-info-text" id="cover-filename">portada.jpg</span>
                <span class="file-clear" onclick="clearCoverFile()">✕</span>
            </div>

            <div class="section-title" style="margin-top: 10px;">
                <svg width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"></path></svg>
                Metadatos del E-book
            </div>

            <div class="setting-group">
                <label for="book-title">Título del Libro *</label>
                <input type="text" id="book-title" class="input-text" placeholder="Ej. Mi Primer E-book">
            </div>

            <div class="row-grid">
                <div class="setting-group">
                    <label for="book-author">Autor(es)</label>
                    <input type="text" id="book-author" class="input-text" placeholder="Ej. Juan Pérez">
                </div>
                <div class="setting-group">
                    <label for="book-publisher">Editorial</label>
                    <input type="text" id="book-publisher" class="input-text" placeholder="Ej. Imprenta Local">
                </div>
            </div>

            <div class="row-grid">
                <div class="setting-group">
                    <label for="book-lang">Idioma (Código ISO)</label>
                    <select id="book-lang" class="select-input">
                        <option value="es" selected>Español (es)</option>
                        <option value="en">Inglés (en)</option>
                        <option value="fr">Francés (fr)</option>
                        <option value="de">Alemán (de)</option>
                        <option value="it">Italiano (it)</option>
                        <option value="pt">Portugués (pt)</option>
                    </select>
                </div>
                <div class="setting-group">
                    <label for="book-rights">Derechos / Licencia</label>
                    <input type="text" id="book-rights" class="input-text" placeholder="Ej. © 2026 Reservados todos los derechos">
                </div>
            </div>

            <div class="setting-group">
                <label for="book-desc">Sinopsis / Descripción</label>
                <textarea id="book-desc" class="textarea-input" placeholder="Escribe una pequeña descripción del contenido..."></textarea>
            </div>

            <div class="section-title" style="margin-top: 15px;">
                <svg width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25"></path></svg>
                Páginas Preliminares (Opcional)
            </div>

            <div class="setting-group">
                <label for="book-copyright">Copyright / Página de Derechos</label>
                <textarea id="book-copyright" class="textarea-input" style="height: 60px;" placeholder="Ej. © 2026 Brenis. Todos los derechos reservados.&#10;Queda prohibida la reproducción total o parcial de esta obra sin autorización..."></textarea>
            </div>

            <div class="setting-group">
                <label for="book-dedication">Dedicatoria</label>
                <textarea id="book-dedication" class="textarea-input" style="height: 60px;" placeholder="Ej. Para mis padres y mentores, quienes hicieron posible este camino..."></textarea>
            </div>

            <div class="setting-group">
                <label for="book-preface">Prefacio / Introducción</label>
                <textarea id="book-preface" class="textarea-input" style="height: 100px;" placeholder="Escribe aquí el prefacio, prólogo o introducción general de tu libro..."></textarea>
            </div>

            <div class="section-title" style="margin-top: 15px;">
                <svg width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4"></path></svg>
                Maquetación y Ajustes
            </div>

            <div class="row-grid">
                <div class="setting-group">
                    <label for="book-theme">Tema de Lectura (CSS)</label>
                    <select id="book-theme" class="select-input">
                        <option value="bookish" selected>Clásico Serif (Novela)</option>
                        <option value="modern">Limpio Sans-Serif (Técnico)</option>
                        <option value="academic">Formal Serif (Académico)</option>
                    </select>
                </div>
                <div class="setting-group">
                    <label for="chapter-level">División de Capítulos</label>
                    <select id="chapter-level" class="select-input">
                        <option value="1">Nivel 1 (encabezado h1)</option>
                        <option value="2" selected>Nivel 2 (encabezado h1 y h2)</option>
                    </select>
                </div>
            </div>

            <div class="row-grid">
                <div class="setting-group">
                    <label for="math-rendering">Fórmulas Matemáticas (Kindle / Ebooks)</label>
                    <select id="math-rendering" class="select-input">
                        <option value="webtex_svg" selected>Imágenes SVG en línea (Infalible para Kindle)</option>
                        <option value="mathml">MathML nativo (Estándar EPUB3)</option>
                        <option value="mathjax">MathJax Javascript (Para navegadores/apps)</option>
                    </select>
                </div>
            </div>

            <div class="row-grid">
                <div class="setting-group" style="display: flex; align-items: center;">
                    <label class="toggle-container">
                        <input type="checkbox" id="book-toc" class="toggle-checkbox" checked onchange="toggleTocOptions()">
                        <div class="toggle-switch"></div>
                        <span class="toggle-label">Generar Índice (TOC)</span>
                    </label>
                </div>
                <div class="setting-group" id="toc-depth-group">
                    <label for="toc-depth">Profundidad del Índice</label>
                    <select id="toc-depth" class="select-input">
                        <option value="1">Título principal (h1)</option>
                        <option value="2">Subtítulos (h2)</option>
                        <option value="3" selected>Secciones (h3)</option>
                    </select>
                </div>
            </div>

            <button id="convert-btn" class="convert-btn" onclick="startConversion()">
                <div class="spinner" id="btn-spinner"></div>
                <span id="btn-text">Convertir a EPUB</span>
            </button>

            <!-- Diagnostic Console -->
            <div class="console-container">
                <div class="console-header" onclick="toggleConsole()">
                    <span>Consola de Pandoc</span>
                    <span id="console-arrow">▼</span>
                </div>
                <div class="console-body" id="console-logs">Preparado. Esperando archivo HTML para procesar...</div>
            </div>
        </div>

        <!-- Right Preview / Status panel -->
        <div class="card preview-card">
            
            <!-- Default Placeholder State -->
            <div class="preview-placeholder" id="preview-placeholder">
                <svg fill="none" stroke="currentColor" stroke-width="1" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25"></path></svg>
                <h3>Listo para Compilar</h3>
                <p>Configura tus metadatos, carga el archivo HTML o ZIP de tu manuscrito y obtén un libro digital EPUB compatible con todos los lectores e-readers.</p>
            </div>

            <!-- Success State -->
            <div class="success-state" id="success-state">
                <div class="success-icon">📖</div>
                <h3 class="success-title">¡EPUB Generado Exitosamente!</h3>
                <p class="success-text" id="success-message">Tu libro electrónico ha sido compilado a formato estándar EPUB 3 por Pandoc y está listo para descargar.</p>
                
                <div class="success-actions">
                    <a href="#" id="download-link" class="download-btn">
                        <svg width="20" height="20" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"></path></svg>
                        Descargar E-book
                    </a>
                    <button class="reset-btn" onclick="resetUI()">Convertir otro libro</button>
                </div>
            </div>

        </div>

    </div>

    <!-- Error Toast Notification -->
    <div class="toast" id="error-toast">Ocurrió un error.</div>

    <script>
        let htmlBase64 = null;
        let coverBase64 = null;
        
        // --- File Input & Drag-and-Drop ---
        // The <label for="inputId"> handles click-to-open natively in all browsers.
        // We only need to wire up the 'change' event and drag-drop visual feedback.

        function setupFileInput(inputId, zoneId, handlerFn) {
            const input = document.getElementById(inputId);
            const zone  = document.getElementById(zoneId);
            if (!input || !zone) return;

            // File selected via click (label triggers this)
            input.addEventListener('change', () => {
                if (input.files.length > 0) {
                    console.log('Archivo seleccionado:', input.files[0].name);
                    handlerFn(input.files[0]);
                }
            });

            // Drag-and-drop support
            zone.addEventListener('dragover', (e) => { e.preventDefault(); zone.classList.add('dragover'); });
            zone.addEventListener('dragleave', ()  => { zone.classList.remove('dragover'); });
            zone.addEventListener('drop', (e) => {
                e.preventDefault();
                zone.classList.remove('dragover');
                if (e.dataTransfer.files.length > 0) handlerFn(e.dataTransfer.files[0]);
            });
        }

        

        // --- File Handlers ---
        function handleHtmlFile(file) {
            const reader = new FileReader();
            reader.onload = function(e) {
                const dataUrl = e.target.result;
                const base64 = dataUrl.split(',')[1];
                htmlBase64 = base64;

                document.getElementById('html-filename').innerText = file.name;
                document.getElementById('html-file-info').style.display = 'flex';

                const titleField = document.getElementById('book-title');
                if (!titleField.value) {
                    const nameOnly = file.name.replace(/\.[^.]+$/, '');
                    titleField.value = nameOnly.replace(/[_-]/g, ' ');
                }
            };
            reader.onerror = function() {
                showToast('Error al leer el archivo HTML/ZIP');
            };
            reader.readAsDataURL(file);
        }

        function handleCoverFile(file) {
            const reader = new FileReader();
            reader.onload = function(e) {
                const dataUrl = e.target.result;
                const base64 = dataUrl.split(',')[1];
                coverBase64 = base64;

                document.getElementById('cover-filename').innerText = file.name;
                document.getElementById('cover-file-info').style.display = 'flex';
            };
            reader.onerror = function() {
                showToast('Error al leer la imagen de portada');
            };
            reader.readAsDataURL(file);
        }

        setupFileInput('html-file-input',  'html-dropzone',  handleHtmlFile);
        setupFileInput('cover-file-input', 'cover-dropzone', handleCoverFile);
        // --- Clear Uploads ---
        function clearHtmlFile() {
            htmlBase64 = null;
            document.getElementById('html-file-input').value = '';
            document.getElementById('html-file-info').style.display = 'none';
        }

        function clearCoverFile() {
            coverBase64 = null;
            document.getElementById('cover-file-input').value = '';
            document.getElementById('cover-file-info').style.display = 'none';
        }

        // --- Layout Toggles ---
        function toggleTocOptions() {
            const isChecked = document.getElementById('book-toc').checked;
            document.getElementById('toc-depth-group').style.opacity = isChecked ? '1' : '0.4';
            document.getElementById('toc-depth').disabled = !isChecked;
        }

        function toggleConsole() {
            const body = document.getElementById('console-logs');
            const arrow = document.getElementById('console-arrow');
            if (body.style.display === 'none') {
                body.style.display = 'block';
                arrow.innerText = '▼';
            } else {
                body.style.display = 'none';
                arrow.innerText = '▲';
            }
        }

        // --- Conversion Flow ---
        function startConversion() {
            const title = document.getElementById('book-title').value.trim();
            if (!htmlBase64) {
                showToast("Por favor carga un archivo HTML o proyecto ZIP.");
                return;
            }
            if (!title) {
                showToast("Por favor ingresa un título para el libro.");
                return;
            }

            // Disable btn
            const btn = document.getElementById('convert-btn');
            const spinner = document.getElementById('btn-spinner');
            const text = document.getElementById('btn-text');
            btn.disabled = true;
            spinner.style.display = 'block';
            text.innerText = 'Compilando...';

            const logs = document.getElementById('console-logs');
            logs.innerText = "[PROCESO] Enviando archivos a Pandoc backend...\\n";

            const payload = {
                html_file: htmlBase64,
                cover_file: coverBase64,
                settings: {
                    title: title,
                    author: document.getElementById('book-author').value.trim(),
                    lang: document.getElementById('book-lang').value,
                    publisher: document.getElementById('book-publisher').value.trim(),
                    rights: document.getElementById('book-rights').value.trim(),
                    description: document.getElementById('book-desc').value.trim(),
                    copyright: document.getElementById('book-copyright').value.trim(),
                    dedication: document.getElementById('book-dedication').value.trim(),
                    preface: document.getElementById('book-preface').value.trim(),
                    theme: document.getElementById('book-theme').value,
                    toc: document.getElementById('book-toc').checked,
                    toc_depth: parseInt(document.getElementById('toc-depth').value),
                    chapter_level: parseInt(document.getElementById('chapter-level').value),
                    math_rendering: document.getElementById('math-rendering').value
                }
            };

            fetch('/convert', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            })
            .then(res => res.json())
            .then(data => {
                btn.disabled = false;
                spinner.style.display = 'none';
                text.innerText = 'Convertir a EPUB';

                if (data.success) {
                    logs.innerText += `[ÉXITO] EPUB Generado exitosamente como: ${data.filename}\\n`;
                    if (data.logs) {
                        logs.innerText += `\\n[PANDOC LOGS]:\\n${data.logs}`;
                    } else {
                        logs.innerText += `\\nSin advertencias de compilación.`;
                    }

                    // Render download links
                    const downloadLink = document.getElementById('download-link');
                    
                    // Decodificar Base64 a Blob
                    const byteCharacters = atob(data.file_data);
                    const byteNumbers = new Array(byteCharacters.length);
                    for (let i = 0; i < byteCharacters.length; i++) {
                        byteNumbers[i] = byteCharacters.charCodeAt(i);
                    }
                    const byteArray = new Uint8Array(byteNumbers);
                    const blob = new Blob([byteArray], { type: data.mime_type });
                    const fileUrl = URL.createObjectURL(blob);

                    downloadLink.href = fileUrl;
                    downloadLink.download = data.filename;

                    document.getElementById('preview-placeholder').style.display = 'none';
                    document.getElementById('success-state').style.display = 'flex';
                    
                    let msg = `Tu e-book "${title}" ha sido compilado a formato estándar EPUB 3 por Pandoc y está listo para descargar.`;
                    if (data.saved_local_path) {
                        msg += `\\n\\nArchivo guardado automáticamente en:\\n${data.saved_local_path}`;
                        logs.innerText = `[SISTEMA LOCAL] Archivo guardado automáticamente en tu carpeta de Descargas:\\n👉 ${data.saved_local_path}\\n\\n` + logs.innerText;
                    }
                    document.getElementById('success-message').innerText = msg;
                } else {
                    logs.innerText += `[FALLO] Pandoc reportó un error:\\n${data.error}`;
                    showToast("Error de conversión. Revisa la consola.");
                }
            })
            .catch(err => {
                btn.disabled = false;
                spinner.style.display = 'none';
                text.innerText = 'Convertir a EPUB';
                logs.innerText += `[ERROR] Error de comunicación HTTP: ${err}\\n`;
                showToast("Error de comunicación con el servidor.");
            });
        }

        function resetUI() {
            document.getElementById('success-state').style.display = 'none';
            document.getElementById('preview-placeholder').style.display = 'flex';
            clearHtmlFile();
            clearCoverFile();
            document.getElementById('book-title').value = '';
            document.getElementById('book-author').value = '';
            document.getElementById('book-publisher').value = '';
            document.getElementById('book-rights').value = '';
            document.getElementById('book-desc').value = '';
            document.getElementById('console-logs').innerText = "Preparado. Esperando archivo HTML para procesar...";
        }

        function showToast(message) {
            const toast = document.getElementById('error-toast');
            toast.innerText = message;
            toast.style.display = 'block';
            setTimeout(() => {
                toast.style.display = 'none';
            }, 3500);
        }
    </script>
</body>
</html>
"""

# ----------------------------------------------------------------------
# Server Startup
# ----------------------------------------------------------------------
def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def start_server():
    port = DEFAULT_PORT
    while is_port_in_use(port):
        print(f"[SERVIDOR] Puerto {port} ocupado, probando {port + 1}...")
        port += 1

    server = ThreadingHTTPServer(('0.0.0.0', port), RequestHandler)
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.daemon = True
    server_thread.start()

    print("=====================================================")
    print("  Iniciando HTML a EPUB Converter...")
    print("=====================================================")
    
    pandoc_path = get_pandoc_path()
    if pandoc_path:
        print(f"[INFO] Pandoc detectado en: {pandoc_path}")
    else:
        print("[AVISO] Pandoc NO fue detectado en las rutas comunes. Asegúrate de tenerlo instalado.")
        
    url = f"http://localhost:{port}"
    print(f"[INFO] Abriendo la aplicación en tu navegador: {url}")
    print(f"[SERVIDOR] Corriendo en {url}")
    print("[SERVIDOR] Presiona Ctrl+C en esta terminal para detenerlo.")
    
    webbrowser.open(url)
    
    # Keep main thread alive
    try:
        while True:
            server_thread.join(timeout=1)
    except KeyboardInterrupt:
        print("\n[SERVIDOR] Deteniendo servidor...")
        server.shutdown()
        print("[SERVIDOR] Servidor detenido exitosamente.")

if __name__ == '__main__':
    start_server()
