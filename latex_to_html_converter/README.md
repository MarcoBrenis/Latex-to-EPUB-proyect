# LaTeX to HTML Converter 📄 ➜ 🌐

Un convertidor de archivos LaTeX (en formato `.zip` o individual) a páginas web HTML responsivas y elegantes. Este convertidor levanta un servidor web local y proporciona una interfaz moderna tipo dashboard para que puedas realizar tus conversiones con facilidad, previsualizar los resultados en tiempo real y descargarlos de inmediato.

---

## Características Recientes e Innovaciones

- **Metadatos y Portada Interactiva:**
  - Permite subir una **Imagen de Portada** (PNG, JPG) que se muestra de forma responsiva al inicio del documento.
  - Genera de forma automática una **Página de Título** minimalista y elegante si se definen los campos de Título, Autor y Editorial.
- **Páginas Preliminares (Front Matter):**
  - Campos dedicados para **Copyright**, **Dedicatoria** y **Prefacio** con formato estilizado.
  - Utiliza reglas CSS de salto de página (`page-break-after: always;`) para asegurar que al imprimir a PDF cada una de estas secciones inicie en una hoja limpia.
- **Título de Índice en Español:**
  - El índice de contenido (TOC) se genera con el título en español **"Índice"** en lugar de "Table of Contents".
- **Interfaz Web Glassmorphism:**
  - Diseño moderno en modo oscuro con soporte para arrastrar y soltar archivos.
- **Enlace de Descarga Directo y Auto-Guardado:**
  - Guarda automáticamente el archivo compilado en la carpeta física de descargas de tu sistema (`~/Downloads/`).
  - Utiliza enlaces `<a>` nativos pre-cargados para evitar bloqueos de seguridad en navegadores de Apple (Safari/WebKit).

---

## Requisitos

1. **Python 3.x**
2. **Pandoc** (Motor de conversión de sintaxis).
   - Instalar en macOS (con Homebrew):
     ```bash
     brew install pandoc
     ```

---

## Instrucciones de Uso

1. Navega hasta la carpeta del proyecto:
   ```bash
   cd latex_to_html
   ```
2. Ejecuta el script:
   ```bash
   python3 latex_to_html.py
   ```
3. La aplicación se abrirá en: **`http://localhost:8080`**

---

## Cómo subir el proyecto a GitHub 🚀

Para publicar este convertidor como un repositorio independiente en tu cuenta de GitHub, sigue estos pasos:

1. Crea un repositorio vacío en tu cuenta de GitHub (ej. llamado `latex-to-html-converter`). **No** le agregues README, `.gitignore` ni licencia en la web para evitar conflictos.
2. Abre la terminal en esta carpeta y ejecuta los siguientes comandos:
   ```bash
   # Agregar el enlace remoto de tu nuevo repositorio de GitHub
   git remote add origin https://github.com/TU_USUARIO/TU_REPOSITORIO.git

   # Renombrar la rama a main (si no está hecho)
   git branch -M main

   # Subir el código a GitHub
   git push -u origin main
   ```
¡Listo! Tu convertidor estará en GitHub y será completamente funcional y privado/público según elijas.
