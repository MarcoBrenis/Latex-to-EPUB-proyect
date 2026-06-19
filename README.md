# LaTeX to EPUB Suite 📄 ➔ 🌐 ➔ 📖

Este repositorio contiene un conjunto de herramientas autónomas desarrolladas en Python 3 para convertir manuscritos científicos y literarios desde **LaTeX** a **HTML** responsivo, y de **HTML** a libros digitales estándar **EPUB 3** altamente compatibles con Kindle, Apple Books, Kobo, entre otros.

Ambos proyectos corren servidores locales independientes mediante una interfaz gráfica tipo Dashboard web moderna y estilizada.

---

## Estructura del Proyecto

*   **`latex_to_html_converter/`**: Compila proyectos LaTeX completos en formato `.zip` a páginas web HTML responsivas con soporte de MathJax 3.
*   **`html_to_epub_converter/`**: Toma archivos o proyectos HTML y los empaqueta en formato estándar EPUB 3, resolviendo errores de compilación habituales del lector Kindle (E21018, W14010, W25001).
*   **`index.html`**: Página de presentación del repositorio.

---

## Características de la Suite

### 1. LaTeX a HTML
*   **Gestión de Codificaciones**: Decodificación segura en cascada para evitar pérdidas de caracteres en español y acentos.
*   **Índice Dinámico (TOC)**: Generación automática de índice lateral en español.
*   **Páginas de Metadatos y Front Matter**: Secciones de Copyright, Dedicatoria y Prefacio configurables desde el dashboard.
*   **Soporte de Ecuaciones**: Integración limpia de MathJax 3 para fórmulas inline y de bloque.

### 2. HTML a EPUB 3 (Optimizado para Kindle)
*   **Sanitizador de Rutas de Imágenes**: URL-decodifica y aplana los directorios de imágenes de forma recursiva para evitar la advertencia de Kindle Previewer `W14010` (recursos no encontrados debido a espacios o caracteres especiales).
*   **Localizador de Ecuaciones SVG**: Descarga las ecuaciones compiladas dinámicamente y las inserta en la carpeta local `media/` del EPUB para resolver el error `W25001`.
*   **Limpiador de Anclas de Navegación**: Limpia etiquetas HTML no deseadas dentro del `nav.xhtml` para garantizar compatibilidad con las directrices de publicación de Amazon (error `E21018`).
*   **Copia en Descargas**: Guarda de forma automática el archivo compilado físicamente en la carpeta de descargas del usuario (`~/Downloads`).

---

## Requisitos de Sistema

1.  **Python 3.x**
2.  **Pandoc**: Utilizado de manera interna como motor de parseo y compilación estructurada.
    *   En macOS se instala fácilmente con Homebrew:
        ```bash
        brew install pandoc
        ```

---

## Guía de Inicio Rápido 🚀

### Correr LaTeX a HTML (Puerto 8084)
```bash
cd latex_to_html_converter
python3 latex_to_html.py
```
Abre en tu navegador: **`http://localhost:8084`**

### Correr HTML a EPUB 3 (Puerto 8081)
```bash
cd html_to_epub_converter
python3 html_to_epub.py
```
Abre en tu navegador: **`http://localhost:8081`**

---

## Licencia y Uso
Desarrollado modularmente usando la biblioteca estándar de Python (sin requerir módulos de terceros vía `pip`). Siéntete libre de clonarlo, adaptarlo o contribuir en ramas dedicadas.
