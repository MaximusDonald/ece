import fitz  # PyMuPDF
import docx
from markdown_it import MarkdownIt
from celery import Celery
from sqlmodel import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from uuid import UUID
from datetime import datetime

from app.core.config import get_settings
from app.core.utils import ensure_uuid
from app.models.document import Document, DocumentExtraction, DocumentStatus
from app.services.minio_client import get_minio_client, download_file
from app.workers.celery_app import celery_app
from app.workers.async_runner import run_async_task
from app.workers.task_dispatch import enqueue_document_task
from app.workers.pipeline_tracker import complete_step, fail_step, start_step

settings = get_settings()

# Sync engine for Celery
# Async engine for Celery tasks
async_engine = create_async_engine(
    settings.database_url,  # Ne supprimez pas +asyncpg ici
    echo=False,
    pool_pre_ping=True,
)

SyncSession = sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)


def extract_pdf(content: bytes) -> tuple[str, int]:
    """Extract text from PDF using PyMuPDF."""
    doc = fitz.open(stream=content, filetype="pdf")
    markdown_parts = []
    page_count = len(doc)
    
    for page_num in range(page_count):
        page = doc[page_num]
        text = page.get_text("text")
        if text.strip():
            markdown_parts.append(f"## Page {page_num + 1}\n\n{text.strip()}")
    
    doc.close()
    return "\n\n".join(markdown_parts), page_count


def extract_docx(content: bytes) -> tuple[str, int]:
    """Extract text from DOCX using python-docx."""
    import io
    doc = docx.Document(io.BytesIO(content))
    markdown_parts = []
    
    for para in doc.paragraphs:
        if para.text.strip():
            # Detect headings by style
            if para.style.name.startswith("Heading"):
                level = int(para.style.name[-1]) if para.style.name[-1].isdigit() else 1
                markdown_parts.append(f"{'#' * level} {para.text}")
            else:
                markdown_parts.append(para.text)
    
    # Simple page estimation
    page_count = max(1, len(markdown_parts) // 10)
    return "\n\n".join(markdown_parts), page_count


def extract_markdown(content: bytes) -> tuple[str, int]:
    """Parse markdown content."""
    text = content.decode("utf-8")
    # Count approximate pages
    page_count = max(1, len(text) // 3000)
    return text, page_count


def calculate_quality_score(markdown: str, page_count: int) -> float:
    """Calculate extraction quality score (0.0-1.0)."""
    if not markdown or not markdown.strip():
        return 0.0
    
    # Simple heuristics
    char_count = len(markdown)
    word_count = len(markdown.split())
    
    # Penalize very short extractions
    if word_count < 50:
        return 0.3
    
    # Check for structure (headings, paragraphs)
    has_headings = "#" in markdown[:500]
    has_multiple_paragraphs = markdown.count("\n\n") > 3
    
    score = 0.5
    if has_headings:
        score += 0.2
    if has_multiple_paragraphs:
        score += 0.2
    if word_count > 500:
        score += 0.1
    
    return min(1.0, score)


def detect_language(text: str) -> str:
    """Simple language detection."""
    # Check for French indicators
    french_words = {"le", "la", "les", "de", "du", "des", "et", "est", "une", "un", "pour", "avec", "sur", "dans", "par", "au", "aux"}
    words = set(text.lower().split()[:200])
    french_count = len(words & french_words)
    
    if french_count > 10:
        return "fr"
    return "en"


async def run_extraction(document_id: UUID) -> None:
    """Run document extraction asynchronously."""
    start_step(document_id, 1, "Lecture du fichier et extraction du texte")
    async with SyncSession() as session:
        # Get document
        document = await session.get(Document, document_id)
        if not document:
            raise RuntimeError("Document introuvable pendant l’extraction")
        
        # Update status
        document.status = DocumentStatus.EXTRACTING
        await session.commit()
        
        try:
            # Download from MinIO
            minio_client = get_minio_client()
            content = download_file(minio_client, document.minio_bucket, document.minio_object)
            
            # Extract based on MIME type
            if document.mime_type == "application/pdf":
                markdown, page_count = extract_pdf(content)
            elif document.mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                markdown, page_count = extract_docx(content)
            else:  # markdown, text
                markdown, page_count = extract_markdown(content)
            
            # Calculate metrics
            quality_score = calculate_quality_score(markdown, page_count)
            language = detect_language(markdown)
            
            # Save or update extraction (idempotent for Celery retries)
            existing_extraction = (
                await session.execute(
                    select(DocumentExtraction).where(DocumentExtraction.document_id == document.id)
                )
            ).scalar_one_or_none()

            if existing_extraction:
                existing_extraction.markdown = markdown
                existing_extraction.quality_score = quality_score
                existing_extraction.page_count = page_count
                existing_extraction.language = language
                session.add(existing_extraction)
            else:
                extraction = DocumentExtraction(
                    document_id=document.id,
                    markdown=markdown,
                    quality_score=quality_score,
                    page_count=page_count,
                    language=language,
                )
                session.add(extraction)
            
            # Update document status
            document.status = DocumentStatus.EXTRACTED
            await session.commit()
            
        except Exception as e:
            document.status = DocumentStatus.FAILED
            await session.commit()
            raise

        complete_step(document.id, 1, "Le texte a été extrait et enregistré")
        start_step(document.id, 2, "Préparation de l’analyse du contenu")
        from app.workers.semantic import semantic_analysis_task
        try:
            enqueue_document_task(semantic_analysis_task, document.id, "semantic")
        except Exception as exc:
            print(f"Unable to queue semantic analysis for {document.id}: {exc}")
            fail_step(document.id, 2)


@celery_app.task(bind=True, max_retries=3)
def extract_document_task(self, document_id):
    """Celery task for document extraction."""
    try:
        run_async_task(run_extraction(ensure_uuid(document_id)), async_engine)
    except Exception as exc:
        fail_step(str(document_id), 1, retrying=self.request.retries < self.max_retries)
        self.retry(exc=exc, countdown=60)
