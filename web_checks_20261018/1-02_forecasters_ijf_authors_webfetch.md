# Snapshot (text extract): IJF "For authors" page

- URL: https://forecasters.org/ijf/authors/ (linked from https://ijf.forecasters.org/ → redirects to https://forecasters.org/ijf/)
- Accessed: 2026-10-26 (UTC)
- Method: raw HTML not obtainable. curl and headless Chromium both received HTTP 403 from the bunny.net "Bunny Shield" challenge ("Establishing a secure connection ... Unexpected error, please reload and try again."). The page was read with the WebFetch tool, which returns a model-generated extract, not raw HTML. Quotes below are as returned by WebFetch; they were requested word-for-word but could not be checked against raw HTML.

## WebFetch output 1 (prompt: reproduce page verbatim — tool declined, gave summary + links)

> I can't reproduce the full main-content text verbatim, but here is a summary of the page's main content, with a few short quotes and key links.
>
> **IIF "For authors" page (International Journal of Forecasting)**
>
> - **Guidelines:** Authors can consult the IJF submission guidelines PDF and the IJF Preferred Keywords list. Submissions are made through Editorial Manager.
> - **Online supplements:** For empirical studies, the method and data descriptions should allow replication. Authors are asked to submit code and data as an online supplement. Additional results can also be supplied as appendixes. Accepted articles' supplements appear on ScienceDirect.
> - **LaTeX:** "LaTeX submissions are encouraged." Authors should use the Elsevier elsarticle template, submit a PDF first, and provide source files after acceptance. References should be handled with BibTeX or BibLaTeX, and figures should be EPS or PDF rather than JPG or WMF.
> - **MS-Word:** "Microsoft Word files are also permitted." Equations should be equation objects rather than graphics, figures should be high resolution, and EndNote users should use APA style.
> - **Blog:** The page lists selected blog posts by Rob J Hyndman, the IJF Editor-in-Chief from 2005 to 2018. ...
>
> Key links from the page:
> - Guidelines: https://pierrepinson.com/IJF/IJFauthorguidelines.pdf
> - Keywords: https://ijf.forecasters.org/keywords/
> - Submission portal: https://www.editorialmanager.com/ijf
> - Elsevier LaTeX instructions: https://www.elsevier.com/authors/author-schemas/latex-instructions
> - Hyndman's blog: https://robjhyndman.com/categories/ijf/

## WebFetch output 2 (prompt: exact quotes per topic)

> **Submission guidelines**
> - "Guidelines for IJF submissions" (https://pierrepinson.com/IJF/IJFauthorguidelines.pdf)
>
> **Preferred keywords**
> - "IJF Preferred Keywords" (https://ijf.forecasters.org/keywords/)
>
> **Editorial Manager**
> - "Submit an article" (https://www.editorialmanager.com/ijf)
>
> **Online supplements, code, data, and replication**
> - "For empirical studies, the description of the method and the data should be sufficient to allow for replication."
> - "Authors are requested to submit computer code and data which can be made available as an online supplement to the paper."
>
> **LaTeX template and reference style**
> - "LaTeX submissions are encouraged."
> - "Please use this template" (https://docs.google.com/uc?id=0B4rHhz_bQTXIQTI4aXNjclUxbHM&export=download)
> - "More instructions about the elsarticle class" (https://www.elsevier.com/__data/assets/pdf_file/0008/56843/elsdoc-1.pdf)
> - "Use BibLaTeX or BibTeX to ensure all cited papers are listed in the bibliography."
> - "If you use EndNote for references, please use the APA style."
>
> **Figure file formats**
> - "Make sure all figures are saved in eps or pdf format."
> - "Do not use jpg or wmf formats."
>
> **Word submissions**
> - "Microsoft Word files are also permitted."
> - "Please ensure equations are saved as equation objects, not as graphics."
> - "Figures should be of high resolution."

## Follow-up checks of linked files (curl, 2026-10-26)

- https://pierrepinson.com/IJF/IJFauthorguidelines.pdf → HTTP 404 (guidelines PDF not available at that address).
- https://docs.google.com/uc?id=0B4rHhz_bQTXIQTI4aXNjclUxbHM&export=download → HTTP 200, ZIP with ijftemplate.tex, ijftemplate.pdf, model5-names.bst, refs.bib. The .tex file is saved as 1-04_ijf_latex_template_ijftemplate.tex.
