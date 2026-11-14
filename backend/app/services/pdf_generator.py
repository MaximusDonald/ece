"""PDF generation service using WeasyPrint."""
import logging
from weasyprint import HTML, CSS
from typing import Optional

for _noisy_logger in ("fontTools", "fontTools.subset", "fontTools.ttLib", "weasyprint"):
    logging.getLogger(_noisy_logger).setLevel(logging.ERROR)


def generate_pdf_from_html(html: str, base_url: str = "") -> bytes:
    """Generate PDF from HTML string."""
    try:
        html_doc = HTML(string=html, base_url=base_url)
        pdf_bytes = html_doc.write_pdf()
        return pdf_bytes
    except Exception as e:
        # Fallback: return minimal PDF
        fallback_html = f"""<!DOCTYPE html>
<html><body><h1>Erreur de génération PDF</h1><p>{str(e)}</p></body></html>"""
        return HTML(string=fallback_html).write_pdf()


def generate_pdf_from_markdown(markdown: str, title: str = "Rapport") -> bytes:
    """Generate PDF from Markdown via HTML conversion."""
    from markdown_it import MarkdownIt
    md = MarkdownIt()
    body_html = md.render(markdown)
    
    full_html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <title>{title}</title>
    <style>
        @page {{ margin: 2cm; size: A4; }}
        body {{ font-family: 'DejaVu Sans', Arial, sans-serif; font-size: 11pt; line-height: 1.6; color: #1e293b; }}
        h1 {{ color: #0052a5; border-bottom: 2px solid #0052a5; padding-bottom: 0.5rem; }}
        h2 {{ color: #003d7a; margin-top: 2rem; }}
        h3 {{ color: #0052a5; }}
        .badge {{ display: inline-block; padding: 0.2rem 0.5rem; border-radius: 9999px; font-size: 0.75rem; font-weight: 600; }}
        .badge-critique {{ background: #fdeaea; color: #c41e3a; }}
        .badge-eleve {{ background: #fff3e0; color: #e67e00; }}
        .badge-modere {{ background: #fff8e1; color: #e6a800; }}
        .badge-a_surveiller {{ background: #e8f1fa; color: #0052a5; }}
        .badge-conforme {{ background: #e8f5ed; color: #007b3f; }}
        pre {{ background: #f1f5f9; padding: 1rem; border-radius: 0.5rem; white-space: pre-wrap; word-break: break-word; }}
        code {{ background: #f1f5f9; padding: 0.1rem 0.3rem; border-radius: 0.25rem; font-family: monospace; }}
        table {{ width: 100%; border-collapse: collapse; margin: 1rem 0; }}
        th, td {{ border: 1px solid #e2e8f0; padding: 0.5rem; text-align: left; }}
        th {{ background: #f8fafc; }}
    </style>
</head>
<body>
    <div class="header" style="text-align: center; margin-bottom: 2rem;">
        <h1>{title}</h1>
        <p>ECO-Compliance Engine</p>
    </div>
    {body_html}
</body>
</html>"""
    
    return generate_pdf_from_html(full_html)