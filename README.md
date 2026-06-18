# Convertidor HTML a EPUB 📖

Una herramienta local, autónoma e interactiva para convertir tus proyectos o manuscritos HTML (incluyendo hojas de estilo locales, imágenes y fuentes) en libros digitales estándar **EPUB 3** listos para cualquier lector digital (e-readers como Apple Books, Kindle o Kobo).

El convertidor está desarrollado utilizando únicamente la biblioteca estándar de Python (sin dependencias de `pip`) y utiliza **Pandoc** de manera local como motor de compilación estructurada.

---

## Características Principales

*   **Doble Formato de Carga**: Acepta un archivo `.html` individual o un archivo `.zip` que contenga un proyecto web completo (ej. `index.html` referenciando carpetas locales como `images/`, `css/` o `fonts/`).
*   **Editor Completo de Metadatos**: Configura de manera visual el Título del libro, Autor(es), Editorial, Idioma (selector ISO), Licencia de Derechos y una Sinopsis/Descripción multilínea.
*   **Gestor de Portadas**: Permite subir de forma opcional una imagen de portada (`.png`, `.jpg` o `.jpeg`) que se incrustará de forma nativa e IDPF-compatible en el contenedor del libro.
*   **Ajustes de Maquetación**:
    *   **Bookish (Clásico Serif)**: Diseñado para novelas clásicas y literatura con tipografía serifada, sangrado elegante de párrafos y márgenes amplios.
    *   **Modern (Sans-Serif)**: Estilo de lectura limpio y espaciado para libros técnicos, tutoriales y documentación de código.
    *   **Academic**: Estilos y márgenes formales con tipografía formal tipo Times New Roman y cabeceras subrayadas.
*   **Configuración Avanzada**:
    *   Generación automática de Índice de Contenidos (TOC) con control de profundidad (h1, h2, h3).
    *   Control del nivel de división de capítulos (creación de secciones lógicas del EPUB basadas en cabeceras `h1` o `h2`).
*   **Consola de Diagnóstico**: Visualización en tiempo real de logs y posibles advertencias reportadas por Pandoc durante el procesamiento.

---

## Requisitos de Sistema

1.  **Python 3** (instalado por defecto en macOS/Linux).
2.  **Pandoc**: Motor de conversión de documentos.
    *   En macOS se instala fácilmente con Homebrew:
        ```bash
        brew install pandoc
        ```
    *   En Windows o Linux, descárgalo desde la [Página Oficial de Pandoc](https://pandoc.org/installing.html).

---

## Cómo Iniciar la Aplicación

1.  Abre una terminal y dirígete al directorio del convertidor.
2.  Inicia el servidor local de Python:
    ```bash
    python3 html_to_epub.py
    ```
3.  La aplicación detectará un puerto libre (por defecto `8081`) e iniciará automáticamente tu navegador web predeterminado en la dirección:
    👉 **http://localhost:8081**

---

## Preparación de tus Archivos HTML

Para garantizar una conversión perfecta de tus proyectos complejos, sigue estas recomendaciones:

*   **Estructura del ZIP**: El archivo ZIP debe contener un archivo principal llamado `index.html` (o al menos un archivo `.html` en la raíz).
*   **Rutas Relativas**: Todas las imágenes, estilos CSS o recursos adicionales deben referenciarse mediante rutas relativas estándar en el HTML:
    ```html
    <link rel="stylesheet" href="css/estilos.css">
    <img src="images/foto.png" alt="Descripción">
    ```
*   **Codificación UTF-8**: Guarda siempre tus archivos HTML con codificación UTF-8 para garantizar que las tildes y caracteres especiales en español se lean de forma correcta.

---

## Pruebas de Integración Automatizadas

Para validar que todo el sistema y la instalación de Pandoc funcionan correctamente, se incluye una suite de pruebas automatizadas:

1.  **Generar entorno de prueba**: Crea un proyecto HTML ficticio con estilos locales, imágenes internas y una portada ejecutando:
    ```bash
    python3 create_test_html_zip.py
    ```
2.  **Correr los tests**: Con el servidor `html_to_epub.py` encendido en segundo plano, ejecuta:
    ```bash
    python3 test_client.py
    ```
El cliente enviará los archivos Base64, esperará la compilación exitosa y analizará el contenedor `.epub` generado (validando la existencia del `mimetype` requerido, esquemas XML y assets multimedia).
