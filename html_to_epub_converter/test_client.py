#!/usr/bin/env python3
import urllib.request
import json
import base64
import os
import sys
import io
import zipfile

def run_test():
    server_url = "http://localhost:8081/convert"
    zip_path = "/Users/brenis/Documents/Codigos - MC-MSA/html_to_epub/test_html_project.zip"
    cover_path = "/Users/brenis/Documents/Codigos - MC-MSA/html_to_epub/test_cover.png"
    
    # Check if files exist
    if not os.path.exists(zip_path):
        print(f"[ERROR] Test ZIP not found at {zip_path}")
        sys.exit(1)
    if not os.path.exists(cover_path):
        print(f"[ERROR] Cover image not found at {cover_path}")
        sys.exit(1)
        
    print(f"Reading test ZIP from {zip_path}...")
    with open(zip_path, 'rb') as f:
        zip_bytes = f.read()
        
    print(f"Reading cover image from {cover_path}...")
    with open(cover_path, 'rb') as f:
        cover_bytes = f.read()
        
    zip_b64 = base64.b64encode(zip_bytes).decode('utf-8')
    cover_b64 = base64.b64encode(cover_bytes).decode('utf-8')
    
    print("\n--- Sending Conversion Request ---")
    payload = {
        "html_file": zip_b64,
        "cover_file": cover_b64,
        "settings": {
            "title": "Manual del Desarrollador MC-MSA",
            "author": "Dr. Assistant & Master Brenis",
            "lang": "es",
            "publisher": "Editorial MC-MSA",
            "rights": "© 2026 Todos los derechos reservados",
            "description": "Esta es la sinopsis detallada del manual de pruebas.",
            "theme": "academic",
            "toc": True,
            "toc_depth": 3,
            "chapter_level": 2
        }
    }
    
    headers = {'Content-Type': 'application/json'}
    req = urllib.request.Request(
        server_url, 
        data=json.dumps(payload).encode('utf-8'), 
        headers=headers,
        method='POST'
    )
    
    try:
        with urllib.request.urlopen(req) as response:
            res_data = json.loads(response.read().decode('utf-8'))
            
        if not res_data.get('success'):
            print(f"[FAIL] Server reported error: {res_data.get('error')}")
            sys.exit(1)
            
        print("[SUCCESS] Conversion API reported success!")
        print(f"Output Filename: {res_data.get('filename')}")
        print(f"Mime-Type: {res_data.get('mime_type')}")
        
        # Verify content bytes
        epub_bytes = base64.b64decode(res_data.get('file_data'))
        
        # Save output for manual inspection
        out_epub_path = "/Users/brenis/Documents/Codigos - MC-MSA/html_to_epub/test_output.epub"
        with open(out_epub_path, 'wb') as f:
            f.write(epub_bytes)
        print(f"Saved generated EPUB book to: {out_epub_path}")
        
        # Verify EPUB Container Structure
        print("\n--- Dissecting EPUB File Container ---")
        epub_io = io.BytesIO(epub_bytes)
        
        if not zipfile.is_zipfile(epub_io):
            print("[FAIL] Output is not a valid ZIP container.")
            sys.exit(1)
            
        with zipfile.ZipFile(epub_io, 'r') as zf:
            file_list = zf.namelist()
            print(f"EPUB files found inside container: {file_list}")
            
            # 1. Verify mimetype file exists and contains correct bytes
            if 'mimetype' not in file_list:
                print("  [FAIL] Missing 'mimetype' file at EPUB root.")
                sys.exit(1)
            else:
                mimetype_val = zf.read('mimetype').decode('utf-8').strip()
                if mimetype_val == 'application/epub+zip':
                    print("  [PASS] 'mimetype' file is correct ('application/epub+zip').")
                else:
                    print(f"  [FAIL] 'mimetype' file has invalid contents: '{mimetype_val}'")
                    sys.exit(1)
            
            # 2. Verify container.xml exists
            if any('container.xml' in f for f in file_list):
                print("  [PASS] XML Container directory ('META-INF/container.xml') detected.")
            else:
                print("  [FAIL] Missing 'META-INF/container.xml' (EPUB standard requirement).")
                sys.exit(1)
                
            # 3. Verify content files (OPF metadata)
            if any(f.endswith('.opf') for f in file_list):
                print("  [PASS] OPF Book Package Metadata file detected.")
            else:
                print("  [FAIL] Missing OPF book structure metadata.")
                sys.exit(1)
                
            # 4. Verify HTML pages exist inside EPUB
            if any(f.endswith(('.xhtml', '.html')) for f in file_list):
                print("  [PASS] Compiled XHTML pages detected inside EPUB.")
            else:
                print("  [FAIL] No XHTML body pages found.")
                sys.exit(1)
                
            # 5. Check if Cover Image is included in EPUB
            cover_exists = any('cover' in f.lower() for f in file_list)
            if cover_exists:
                print("  [PASS] Embedded cover image detected inside EPUB structure.")
            else:
                print("  [FAIL] No cover image found inside EPUB.")
                sys.exit(1)
                
    except Exception as e:
        print(f"[FAIL] HTTP Request failed: {e}")
        sys.exit(1)
        
    print("\n==========================================")
    print("  ALL EPUB CONVERTER TESTS PASSED!")
    print("==========================================")

if __name__ == '__main__':
    run_test()
