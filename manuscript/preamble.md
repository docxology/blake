# LaTeX Preamble

This file contains LaTeX packages and commands injected into the document compilation
process. It is parsed by `infrastructure/rendering/_pdf_latex_helpers.py` and combined
with the configuration by `infrastructure/rendering/pdf_renderer.py` before final
Pandoc execution. Page geometry is owned by `manuscript/config.yaml` so the rendered
TeX has one margin declaration.

```latex
% Core mathematics
\usepackage{amsmath}
\usepackage{amssymb}
\usepackage{amsfonts}

% Document layout
\usepackage{float}
\usepackage{graphicx}

% Tables
\usepackage{booktabs}
\usepackage{longtable}
\usepackage{array}

% Typography and formatting
\usepackage{microtype}
\usepackage{fontsize}
\changefontsize[10.6pt]{8.7pt}
\usepackage{xcolor}
\setlength{\parindent}{0pt}
\setlength{\parskip}{0.55em plus 0.1em minus 0.05em}

% Cross-references and citations
\usepackage{hyperref}
\hypersetup{
    colorlinks=true,
    linkcolor=red,
    citecolor=red,
    urlcolor=red,
    anchorcolor=red,
    filecolor=red
}
\usepackage[capitalise,noabbrev]{cleveref}
\usepackage{natbib}
```
