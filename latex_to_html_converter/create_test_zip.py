#!/usr/bin/env python3
import os
import base64
import zipfile
import io

# 1. Base64 for a tiny valid PNG image (a 100x100 light blue square)
TINY_PNG_B64 = (
    "iVBORw0KGgoAAAANSUhEUgaAAABkAAAAyAQMAAAD+wgnPAAAABlBMVEUAgICAgID"
    "Q0ND///+3aN0HAAAACXBIWXMAAAsTAAALEwEAmpwYAAAAB3RJTUUHMAYdFxUQCxU"
    "9+wAAAB1pVFh0Q29tbWVudAAAAAAAQ3JlYXRlZCB3aXRoIEdJTVBkLmXRAAAAMU"
    "lEQVQ4y2NgQAD8D/hAIoMIIBKhIuA/EEoMRAAhiY0IIDYigNiIAGIjAoihVAAAPW"
    "xNDV677CcAAAAASUVORK5CYII="
)

# Alternative standard tiny blue PNG if the above has padding issues
TINY_PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAGQAAABkCAYAAABw4pVUAAAABmJLR0QA/wD/AP+g"
    "vaeTAAAACXBIWXMAAAsTAAALEwEAmpwYAAAAB3RJTUUHMAYdFxUQCxU9+wAAAB1p"
    "VFh0Q29tbWVudAAAAAAAQ3JlYXRlZCB3aXRoIEdJTVBkLmXRAAAA4ElEQVR42u3c"
    "vQ2DMBiF0e8xWIBBCGbhEizDCExDGWZgEQYgGAIRUqRM5K+IokQ4pxPdrwM+50vK"
    "85ECAAAAAAAA6D2vfd+P/VpXh9vjXg+l1C3H/TzH3/b4nufWdV2O+12Oz3lubdvi"
    "uNvn5Tnv7fP1/X9f/211uD3u9VBK3XLcz3P8bY/veW5d1+W43+X4nOfWti2Ou31e"
    "nvPePl/f//f131aH2+NeD6XULcf9PMff9vie59Z1XY77XY7Pee5j29q2xXG3z8tz"
    "3tvn6/v/vv7b6nB73OuhlLrleG0AAAAAAADQe577vqeqA5w3z5n7vWvEAAAAAElF"
    "TkSuQmCC"
)

# 2. Sample main.tex file with rich LaTeX features
LATEX_CONTENT = r"""\documentclass{article}
\usepackage[utf8]{inputenc}
\usepackage{graphicx}
\usepackage{amsmath}
\usepackage{amssymb}
\usepackage{booktabs}

\title{LaTeX to HTML Converter Test Document}
\author{Dr. Assistant \& Master Brenis}
\date{June 2026}

\begin{document}

\maketitle

\begin{abstract}
Este documento sirve como un caso de prueba para validar el convertidor de LaTeX a HTML. Contiene varios componentes estándar de LaTeX, incluyendo encabezados con acentos, ecuaciones matemáticas en línea y en bloque, tablas, listas y una figura gráfica.
\end{abstract}

\section{Introducción}\label{sec:intro}
¡Bienvenido a la prueba del convertidor! En la redacción científica y matemática, es esencial que las etiquetas estructurales, la bibliografía y las referencias cruzadas se traduzcan con precisión y sin errores de codificación.

Hasta aquí nada del otro mundo, solo hacemos lo que ya sabemos; pero usando la ecuación \ref{eq:integral}, sea la función $f(x)$ integrable. También podemos verificar cómo se renderizan otros caracteres en español como: canción, ecuación, relación, área, música y aquí.

\section{Ecuaciones Matemáticas}\label{sec:math}
Aquí hay una lista de ecuaciones para verificar la renderización de MathJax y la numeración automática.

Primero, una ecuación numerada estándar usando el entorno \texttt{equation}:
\begin{equation}\label{eq:integral}
\int_{a}^{b} f(x) \, dx = F(b) - F(a)
\end{equation}

Podemos referenciar la ecuación anterior como la ecuación \ref{eq:integral} (o con paréntesis como \eqref{eq:integral}).

Siguiente, una ecuación sin numerar:
\[
\sum_{n=1}^{\infty} \frac{1}{n^2} = \frac{\pi^2}{6}
\]

También podemos representar un sistema de ecuaciones lineales usando el entorno \texttt{align}:
\begin{align}\label{eq:linearsystem}
3x + 2y - z &= 1 \\
2x - 2y + 4z &= -2 \\
-x + \frac{1}{2}y - z &= 0
\end{align}

Podemos hacer referencia a este sistema de ecuaciones mediante su identificador: \ref{eq:linearsystem}.

\section{Recursos Visuales}\label{sec:visual}
En esta sección, incluimos un archivo de imagen local. Como se observa en la figura \ref{fig:test_square}, los formatos amigables con la web como PNG se incrustan de forma autónoma.

\begin{figure}[h]
    \centering
    \includegraphics[width=0.5\textwidth]{test_image.png}
    \caption{Un simple cuadrado azul que actúa como imagen de prueba.}
    \label{fig:test_square}
\end{figure}

\section{Datos Estructurados (Tablas)}\label{sec:tables}
Las tablas de LaTeX se traducen a tablas limpias de HTML. La tabla \ref{tab:results} representa métricas de rendimiento del clasificador:

\begin{table}[h]
    \centering
    \begin{tabular}{llrr}
        \toprule
        Método & Dataset & Precisión & Tiempo (s) \\
        \midrule
        MC-MSA v1.0 & popular & 84.5\% & 124.2 \\
        MC-MSA v2.0 & popular & 89.1\% & 98.4 \\
        MC-MSA v2.5 & popular & 92.4\% & 74.0 \\
        \bottomrule
    \end{tabular}
    \caption{Comparación de rendimiento del análisis de similitud melódica.}
    \label{tab:results}
\end{table}

\section{Conclusión}
Como explicamos en la sección \ref{sec:intro}, la correcta traducción de las referencias cruzadas es vital. Si puedes ver la ecuación \ref{eq:integral} correctamente referenciada en la Introducción, y la figura \ref{fig:test_square} referenciada en la sección \ref{sec:visual}, ¡el convertidor ha solucionado los problemas de referencias cruzadas y de acentos (como en ecuación y aquí) con total éxito!

\begin{thebibliography}{9}
\bibitem{knuth84}
Donald E. Knuth, \emph{The \TeX{}book}, Addison-Wesley, 1984.
\end{thebibliography}

\end{document}
"""

def create_zip():
    dest_path = '/Users/brenis/Documents/Codigos - MC-MSA/latex_to_html/test_document.zip'
    print(f"Creating test ZIP archive at: {dest_path}")
    
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        # Write main.tex
        zip_file.writestr('main.tex', LATEX_CONTENT)
        # Write test_image.png
        zip_file.writestr('test_image.png', TINY_PNG_BYTES)
        
    zip_buffer.seek(0)
    with open(dest_path, 'wb') as f:
        f.write(zip_buffer.read())
    print("Test ZIP file created successfully.")

if __name__ == '__main__':
    create_zip()
