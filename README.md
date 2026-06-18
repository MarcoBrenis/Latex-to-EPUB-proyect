# Convertidor HTML a EPUB 📖

Una herramienta local, autónoma e interactiva para convertir tus proyectos o manuscritos HTML (incluyendo hojas de estilo locales, imágenes y fuentes) en libros digitales estándar **EPUB 3** listos para cualquier lector digital (e-readers como Apple Books, Kindle o Kobo).

El convertidor está desarrollado utilizando únicamente la biblioteca estándar de Python (sin dependencias de `pip`) y utiliza **Pandoc** de manera local como motor de compilación estructurada.

---

## Características Principales y Recientes

*   **Páginas Preliminares (Front Matter) Avanzadas**:
    *   Campos dedicados para **Copyright**, **Dedicatoria** y **Prefacio** / Introducción.
    *   La herramienta genera automáticamente archivos XHTML independientes (`00_copyright.html`, `00_dedication.html`, `00_preface.html`) y los inyecta al inicio de la compilación de Pandoc.
    *   Incluye encabezados lógicos invisibles para forzar a los e-readers a **paginar y dividir las páginas preliminares correctamente** (cada una en su respectiva pantalla).
*   **Gestor de Portadas**: Permite subir de forma opcional una imagen de portada (`.png`, `.jpg` o `.jpeg`) que se incrustará de forma nativa e IDPF-compatible en el contenedor del libro.
*   **Título de Índice en Español**: Configuración de `toc-title: "Índice"` para asegurar que la tabla de contenidos generada por Pandoc esté traducida correctamente.
*   **Auto-Guardado Físico**: Al convertir, el archivo `.epub` se guarda automáticamente y de manera física en la carpeta de Descargas del sistema (`~/Downloads/`).

---

## Requisitos de Sistema

1.  **Python 3**
2.  **Pandoc**: Motor de conversión de documentos.
    *   En macOS se instala con Homebrew:
        ```bash
        brew install pandoc
        ```

---

## Cómo Iniciar la Aplicación

1.  Abre una terminal y navega hasta el directorio del convertidor.
2.  Inicia el servidor local:
    ```bash
    python3 html_to_epub.py
    ```
3.  La aplicación se abrirá en tu navegador en:
    👉 **http://localhost:8081**

---

## Cómo subir el proyecto a GitHub 🚀

Para publicar este convertidor como un repositorio independiente en tu cuenta de GitHub, sigue estos pasos:

1. Crea un repositorio vacío en tu cuenta de GitHub (ej. llamado `html-to-epub-converter`). **No** le agregues README ni licencia en la web.
2. Abre la terminal en esta carpeta y ejecuta los siguientes comandos:
   ```bash
   # Agregar el enlace remoto de tu nuevo repositorio de GitHub
   git remote add origin https://github.com/TU_USUARIO/TU_REPOSITORIO.git

   # Renombrar la rama a main
   git branch -M main

   # Subir el código a GitHub
   git push -u origin main
   ```
¡Listo! Tu convertidor de EPUB estará en GitHub y listo para ser usado por ti o tus colaboradores.
