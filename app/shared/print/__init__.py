import io
from flask import render_template
from weasyprint import HTML, default_url_fetcher


def _safe_url_fetcher(url):
    return default_url_fetcher(url, timeout=10)


def render_pdf(template_name, context, base_url=None):
    html = render_template(template_name, **context)
    pdf_io = io.BytesIO()
    HTML(
        string=html,
        base_url=base_url,
        url_fetcher=_safe_url_fetcher,
    ).write_pdf(pdf_io)
    pdf_io.seek(0)
    return pdf_io
