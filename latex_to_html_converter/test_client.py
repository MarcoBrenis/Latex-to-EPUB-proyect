#!/usr/bin/env python3
import urllib.request
import json
import base64
import os
import sys
import io

def run_test():
    import socket
    port = 8080
    for p in range(8080, 8095):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.1)
        result = s.connect_ex(('127.0.0.1', p))
        s.close()
        if result == 0:
            try:
                with urllib.request.urlopen(f"http://localhost:{p}/", timeout=0.5) as r:
                    html_data = r.read().decode('utf-8', errors='ignore')
                    if "LaTeX" in html_data and "HTML" in html_data:
                        port = p
                        print(f"[INFO] Detected LaTeX to HTML converter server running on port {port}")
                        break
            except Exception:
                pass

    server_url = f"http://localhost:{port}/convert"
    zip_path = "/Users/brenis/Documents/Codigos - MC-MSA/latex_to_html/test_document.zip"
    
    if not os.path.exists(zip_path):
        print(f"[ERROR] Test ZIP not found at {zip_path}")
        sys.exit(1)
        
    print(f"Reading test ZIP from {zip_path}...")
    with open(zip_path, 'rb') as f:
        zip_bytes = f.read()
        
    zip_b64 = base64.b64encode(zip_bytes).decode('utf-8')
    
    # Test case 1: Single HTML with Academic theme, TOC, and MathJax
    print("\n--- Test 1: Academic Theme, Single HTML (Embedded Images) ---")
    payload = {
        "zip_file": zip_b64,
        "settings": {
            "theme": "academic",
            "toc": True,
            "equations": True,
            "mathjax": True,
            "format": "single"
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
            
        print("[SUCCESS] Conversion succeeded!")
        print(f"Output Filename: {res_data.get('filename')}")
        print(f"Mime-Type: {res_data.get('mime_type')}")
        
        # Verify content
        html_bytes = base64.b64decode(res_data.get('file_data'))
        html_content = html_bytes.decode('utf-8')
        
        # Verify presence of key elements
        checks = {
            "Title": "LaTeX to HTML Converter Test Document",
            "Spanish Accents (ecuación)": "ecuación",
            "Spanish Accents (aquí)": "aquí",
            "Resolved Section Citation": "sección 1",
            "Resolved Equation Citation": "\\ref{eq:integral}",
            "Resolved Figure Citation": "figura 1",
            "Resolved Table Citation": "tabla 1",
            "MathJax Config": "window.MathJax",
            "MathJax Script tag": "mathjax",
            "Academic CSS Theme": "Georgia",
            "Embedded image data URL": "src=\"data:image/png;base64,",
            "Table element": "table",
            "Table of Contents block": "id=\"TOC\""
        }
        
        failed = False
        for name, pattern in checks.items():
            if pattern in html_content:
                print(f"  [PASS] Found: {name}")
            else:
                print(f"  [FAIL] Missing: {name}")
                failed = True
                
        # Save output for manual review
        out_html_path = "/Users/brenis/Documents/Codigos - MC-MSA/latex_to_html/test_output.html"
        with open(out_html_path, 'wb') as f:
            f.write(html_bytes)
        print(f"Saved test output HTML to: {out_html_path}")
        
        if failed:
            print("[FAIL] Some checks failed in the output HTML content.")
            sys.exit(1)
            
    except Exception as e:
        print(f"[FAIL] HTTP Request failed: {e}")
        sys.exit(1)
        
    # Test case 2: ZIP output with Sleek Dark theme
    print("\n--- Test 2: Sleek Dark Theme, ZIP Bundle (External Images) ---")
    payload['settings']['theme'] = 'dark'
    payload['settings']['format'] = 'zip'
    
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
            
        print("[SUCCESS] ZIP Conversion succeeded!")
        print(f"Output Filename: {res_data.get('filename')}")
        print(f"Mime-Type: {res_data.get('mime_type')}")
        
        zip_bytes = base64.b64decode(res_data.get('file_data'))
        
        # Verify it's a valid ZIP and contains the HTML and PNG image
        import zipfile
        zip_io = io.BytesIO(zip_bytes)
        with zipfile.ZipFile(zip_io, 'r') as zf:
            file_list = zf.namelist()
            print(f"ZIP Contents: {file_list}")
            
            html_in_zip = False
            image_in_zip = False
            for f in file_list:
                if f.endswith('.html'):
                    html_in_zip = True
                if f.endswith('.png'):
                    image_in_zip = True
                    
            if html_in_zip and image_in_zip:
                print("  [PASS] ZIP contains both HTML and PNG assets.")
            else:
                print(f"  [FAIL] ZIP is missing required assets. HTML found: {html_in_zip}, PNG found: {image_in_zip}")
                sys.exit(1)
                
        # Save output ZIP for manual review
        out_zip_path = "/Users/brenis/Documents/Codigos - MC-MSA/latex_to_html/test_output.zip"
        with open(out_zip_path, 'wb') as f:
            f.write(zip_bytes)
        print(f"Saved test output ZIP to: {out_zip_path}")
        
    except Exception as e:
        print(f"[FAIL] HTTP Request failed: {e}")
        sys.exit(1)
        
    print("\n==========================================")
    print("  ALL TESTS COMPLETED SUCCESSFULLY!")
    print("==========================================")

if __name__ == '__main__':
    run_test()
