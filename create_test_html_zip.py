#!/usr/bin/env python3
import os
import zipfile
import base64
import io

# 100x100 Solid Light Blue PNG Base64
TINY_PNG_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAGQAAABkAQMAAABKLAcXAAAABlBMVEUAMwD///+K79CjAAAAAnRSTlMA"
    "AHaTzTgAAAAOSURBVDjXY2AYBYyCAwAAeAAB5/ZlEwAAAABJRU5ErkJggg=="
)

HTML_CONTENT = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Manual del Desarrollador MC-MSA</title>
    <link rel="stylesheet" href="css/custom_styles.css">
</head>
<body>

    <h1>Manual del Desarrollador MC-MSA</h1>
    <p class="author">Por Dr. Assistant & Master Brenis</p>
    
    <h2>Capítulo 1: Introducción al SSM</h2>
    <p>El Análisis de Similitud Melódica (Melodic Similarity Structural Analysis o MC-MSA) es un marco algorítmico diseñado para clasificar y delimitar fronteras melódicas en archivos de audio digital.</p>
    <p>A través de la matriz de similitud de auto-percepción (Self-Similarity Matrix - SSM), podemos identificar patrones repetitivos e incidentes homólogos en canciones populares y piezas clásicas.</p>
    
    <div class="image-container">
        <img src="images/logo.png" alt="Logotipo de MC-MSA" />
        <p class="caption">Figura 1.1: Logotipo esquemático del proyecto.</p>
    </div>

    <h2>Capítulo 2: Algoritmos de Extracción</h2>
    <p>La precisión de la clasificación depende en gran parte del método de extracción de frecuencia fundamental ($f_0$).</p>
    <p>En la siguiente tabla se muestran los resultados comparativos entre las versiones de prueba:</p>

    <table>
        <thead>
            <tr>
                <th>Método</th>
                <th>Precisión</th>
                <th>Latencia (s)</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>MC-MSA v1.0</td>
                <td>84.5%</td>
                <td>124.2</td>
            </tr>
            <tr>
                <td>MC-MSA v2.5 (FCN-f0)</td>
                <td>92.4%</td>
                <td>74.0</td>
            </tr>
        </tbody>
    </table>

    <blockquote>
        "La homogeneidad estructural y la repetición periódica constituyen los dos pilares fundamentales del análisis de similitud melódica."
    </blockquote>

    <h2>Capítulo 3: Conclusiones</h2>
    <p>Este libro electrónico EPUB demuestra que la integración de Pandoc permite compilar archivos con acentos en español (ecuación, relación, aquí) de forma exitosa y preservando la codificación UTF-8 nativa en todo momento.</p>

</body>
</html>
"""

CSS_CONTENT = """/* Estilos personalizados para el manuscrito HTML */
.author {
    font-style: italic;
    text-align: center;
    color: #666666;
    margin-bottom: 2em;
}
.image-container {
    text-align: center;
    margin: 2em 0;
}
.caption {
    font-size: 0.9em;
    color: #555555;
    margin-top: 0.5em;
}
"""

def build_test_environment():
    base_dir = "/Users/brenis/Documents/Codigos - MC-MSA/html_to_epub"
    os.makedirs(base_dir, exist_ok=True)
    
    zip_path = os.path.join(base_dir, "test_html_project.zip")
    cover_path = os.path.join(base_dir, "test_cover.png")
    
    print(f"Creating test assets in: {base_dir}")
    
    # 1. Save Cover Image
    cover_bytes = base64.b64decode(TINY_PNG_B64)
    with open(cover_path, 'wb') as f:
        f.write(cover_bytes)
    print(f"  [OK] Cover image created at: {cover_path}")
    
    # 2. Build ZIP package
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        # Write HTML
        zf.writestr("index.html", HTML_CONTENT)
        # Write CSS
        zf.writestr("css/custom_styles.css", CSS_CONTENT)
        # Write PNG
        zf.writestr("images/logo.png", cover_bytes)
        
    with open(zip_path, 'wb') as f:
        f.write(zip_buffer.getvalue())
    print(f"  [OK] Test ZIP archive created at: {zip_path}")
    print("Test environment generated successfully.")

if __name__ == '__main__':
    build_test_environment()
