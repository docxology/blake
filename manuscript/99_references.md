# References and Cited Authorities {#sec:references}

The bibliography lives in [`manuscript/references.bib`](references.bib) and is read by
Pandoc during the PDF render. The build invokes Pandoc with `--natbib`, so every bracketed
citation marker in the manuscript body is rewritten to the appropriate `\cite`/`\citep`/`\citet`
command and resolved against the bib file. The reference list is emitted automatically below
this heading at render time.
