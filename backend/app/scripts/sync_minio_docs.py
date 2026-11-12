import asyncio
import hashlib
import logging
from uuid import UUID, uuid4
import fitz  # PyMuPDF
from sqlalchemy import select

from app.services.minio_client import get_minio_client
from app.services.legal_extractor import LegalLLMExtractor
from app.core.database import async_session_maker
from app.models.legal import LegalSource, LegalLevel, SourceStatus

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sync_minio")

MINIO_BUCKET = "legal-sources"
APDP_PORTAL_ID = UUID("c709210e-b5f1-4486-9bf1-20f56512309c")
CEDEAO_PORTAL_ID = UUID("b0212491-ecd0-4d5e-adde-d6c4db291b0b")


async def sync_all_minio_documents():
    client = get_minio_client()
    extractor = LegalLLMExtractor()

    # 1. Fetch existing indexed documents
    async with async_session_maker() as session:
        result = await session.execute(
            select(LegalSource.original_filename, LegalSource.minio_object_path, LegalSource.content_hash)
            .where(LegalSource.is_portal == False)
        )
        existing_rows = result.all()
        indexed_filenames = {r[0].strip().lower() for r in existing_rows if r[0]}
        indexed_paths = {r[1].strip() for r in existing_rows if r[1]}
        indexed_hashes = {r[2].strip() for r in existing_rows if r[2]}
        logger.info("Found %d already indexed documents in database.", len(existing_rows))

    # 2. List objects in MinIO
    objects = list(client.list_objects(MINIO_BUCKET, recursive=True))
    logger.info("Found %d total objects in MinIO bucket '%s'.", len(objects), MINIO_BUCKET)

    indexed_count = 0
    skipped_count = 0
    error_count = 0

    for obj in objects:
        obj_name = obj.object_name
        full_path = f"{MINIO_BUCKET}/{obj_name}"
        
        # Extract filename from obj_name (e.g. "bj/0b4f7c4223e0_dpo_et_droits_des_personnes.pdf")
        filename_raw = obj_name.split("/")[-1]
        # Remove sha prefix if present (e.g. "0b4f7c4223e0_...")
        if "_" in filename_raw and len(filename_raw.split("_")[0]) == 12:
            clean_filename = filename_raw.split("_", 1)[1]
        else:
            clean_filename = filename_raw

        if full_path in indexed_paths or clean_filename.strip().lower() in indexed_filenames:
            skipped_count += 1
            continue

        try:
            # Download file from MinIO
            response = client.get_object(MINIO_BUCKET, obj_name)
            content_bytes = response.read()
            response.close()
            response.release_conn()

            sha256 = hashlib.sha256(content_bytes).hexdigest()
            if sha256 in indexed_hashes:
                logger.info("Skipping duplicate content hash for %s", clean_filename)
                skipped_count += 1
                continue

            # Extract text with PyMuPDF
            text = ""
            try:
                doc = fitz.open(stream=content_bytes, filetype="pdf")
                text_parts = [p.get_text("text") for p in doc]
                text = "\n".join(text_parts).strip()
                doc.close()
            except Exception as e:
                logger.warning("Could not extract text from %s: %s", obj_name, e)
                text = f"Document légal archivé : {clean_filename}"

            # Instant heuristic analysis (no network, no LLM quota consumed)
            analysis = extractor._heuristic_fallback(text, clean_filename)

            # Determine parent portal
            fn_lower = clean_filename.lower()
            text_lower = text[:1000].lower()
            if "cedeao" in fn_lower or "ecowas" in fn_lower or "cedeao" in text_lower or "ecowas" in text_lower:
                parent_id = CEDEAO_PORTAL_ID
                country_code = None
                default_authority = "CEDEAO"
                base_url = "https://ecowas.int/documentations/"
            else:
                parent_id = APDP_PORTAL_ID
                country_code = "BJ"
                default_authority = "APDP Bénin"
                base_url = "https://service.apdp.bj/documentations/"

            clean_article_ref = (analysis.act_number or clean_filename)[:250]
            clean_title = (analysis.official_title or clean_filename)[:490]
            authority = (analysis.authority or default_authority)[:250]

            async with async_session_maker() as session:
                new_doc = LegalSource(
                    id=uuid4(),
                    title=clean_title,
                    authority=authority,
                    country_code=country_code,
                    level=LegalLevel(analysis.legal_level),
                    article_ref=clean_article_ref,
                    url_official=f"{base_url}{clean_filename}"[:1000],
                    download_url=f"{base_url}{clean_filename}"[:1000],
                    original_filename=clean_filename[:500],
                    minio_object_path=full_path[:500],
                    content_hash=sha256,
                    content_text=text,
                    status=SourceStatus.VERIFIED if analysis.key_articles else SourceStatus.TO_VERIFY,
                    embedding=[0.0] * 1536,
                    is_portal=False,
                    parent_source_id=parent_id,
                    summary=analysis.executive_summary,
                    legal_terms={"terms": analysis.legal_terms},
                    extracted_articles=analysis.key_articles,
                    crawl_depth=1,
                )
                session.add(new_doc)
                await session.commit()

            indexed_filenames.add(clean_filename.strip().lower())
            indexed_paths.add(full_path)
            indexed_hashes.add(sha256)
            indexed_count += 1
            if indexed_count % 10 == 0:
                logger.info("Indexed %d documents...", indexed_count)

        except Exception as exc:
            logger.error("Failed to sync %s: %s", obj_name, exc)
            error_count += 1

    logger.info("=== Synchronization Completed ===")
    logger.info("Indexed: %d | Skipped: %d | Errors: %d", indexed_count, skipped_count, error_count)


if __name__ == "__main__":
    asyncio.run(sync_all_minio_documents())
