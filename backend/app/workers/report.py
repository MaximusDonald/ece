from celery import Celery
from sqlmodel import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from uuid import UUID
from datetime import datetime
from typing import List
import asyncio

from app.core.config import get_settings
from app.models.legal import RiskFinding, ReportVersion
from app.services.minio_client import get_minio_client, upload_file, get_bucket_name
from app.services.pdf_generator import generate_pdf_from_html
from app.workers.celery_app import celery_app

settings = get_settings()

sync_engine = create_async_engine(
    settings.database_url.replace("+asyncpg", ""),
    echo=False,
    pool_pre_ping=True,
)

SyncSession = sessionmaker(sync_engine, class_=AsyncSession, expire_on_commit=False)


async def run_report_generation(report_version_id: UUID) -> None:
    """Generate PDF reports from Markdown."""
    async with SyncSession() as session:
        report = await session.get(ReportVersion, report_version_id)
        if not report:
            return
        
        try:
            # Generate PDFs
            minio_client = get_minio_client()
            bucket_name = get_bucket_name(str(report.project.org_id), "reports")
            
            # Report 1: Findings
            html1 = markdown_to_html(report.report1_markdown, "Rapport d'Analyse Documentaire")
            pdf1_bytes = generate_pdf_from_html(html1)
            pdf1_object = f"{report_version_id}/report1_findings.pdf"
            upload_file(minio_client, bucket_name, pdf1_object, pdf1_bytes, "application/pdf")
            
            # Report 2: Legal Synthesis
            html2 = markdown_to_html(report.report2_markdown, "Synthèse Juridique & Réglementaire")
            pdf2_bytes = generate_pdf_from_html(html2)
            pdf2_object = f"{report_version_id}/report2_legal.pdf"
            upload_file(minio_client, bucket_name, pdf2_object, pdf2_bytes, "application/pdf")
            
            # Update report with PDF paths
            report.report1_pdf_minio = pdf1_object
            report.report2_pdf_minio = pdf2_object
            await session.commit()
            
        except Exception as e:
            print(f"Report generation error: {e}")
            # Non-blocking - reports still available in Markdown


def markdown_to_html(markdown: str, title: str) -> str:
    """Convert Markdown to styled HTML for PDF generation."""
    from markdown_it import MarkdownIt
    md = MarkdownIt()
    body_html = md.render(markdown)
    
    return f"""<!DOCTYPE html>
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
        .badge-high {{ background: #e8f5ed; color: #007b3f; }}
        .badge-medium {{ background: #fff8e1; color: #e6a800; }}
        .badge-low {{ background: #fdeaea; color: #c41e3a; }}
        pre {{ background: #f1f5f9; padding: 1rem; border-radius: 0.5rem; overflow-x: auto; }}
        code {{ background: #f1f5f9; padding: 0.1rem 0.3rem; border-radius: 0.25rem; font-family: monospace; }}
        table {{ width: 100%; border-collapse: collapse; margin: 1rem 0; }}
        th, td {{ border: 1px solid #e2e8f0; padding: 0.5rem; text-align: left; }}
        th {{ background: #f8fafc; }}
        .header {{ text-align: center; margin-bottom: 2rem; }}
        .footer {{ text-align: center; margin-top: 2rem; font-size: 0.875rem; color: #64748b; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>{title}</h1>
        <p>ECO-Compliance Engine — {datetime.utcnow().strftime('%d/%m/%Y %H:%M')}</p>
    </div>
    {body_html}
    <div class="footer">
        <p>Généré automatiquement par ECO-Compliance Engine — Document confidentiel</p>
    </div>
</body>
</html>"""


@celery_app.task(bind=True, max_retries=2)
def report_generation_task(self, report_version_id: str):
    """Celery task for report generation."""
    try:
        asyncio.run(run_report_generation(UUID(report_version_id)))
    except Exception as exc:
        self.retry(exc=exc, countdown=60)