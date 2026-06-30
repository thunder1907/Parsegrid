import asyncio
import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.database import Document, ExtractedData
from services.llm_extractor import LLMExtractionError, run_structured_extraction
from services.pdf_reader import PDFReaderError, extract_pdf_text

# Configure a module-level logger
logger = logging.getLogger(__name__)


async def _set_document_status(doc_id: UUID, status: str, db_session: AsyncSession) -> Optional[Document]:
    """
    Helper function to safely update the status of a document with explicit commit management.
    """
    try:
        stmt = select(Document).where(Document.id == doc_id)
        result = await db_session.execute(stmt)
        document = result.scalar_one_or_none()
        
        if not document:
            logger.error(f"Document with ID {doc_id} not found in database.")
            return None

        document.status = status
        await db_session.commit()
        logger.info(f"Document {doc_id} status successfully updated to '{status}'.")
        return document
    except Exception as e:
        logger.error(f"Database error while updating document {doc_id} status to '{status}': {e}")
        await db_session.rollback()
        return None


async def process_document_pipeline(doc_id: UUID, file_path: str, db_session: AsyncSession) -> None:
    """
    Executes the complete document processing orchestration workflow:
    1. Update status to 'processing'
    2. Extract raw text from the PDF file
    3. Run structured LLM extraction via Gemini
    4. Save validated data to the extracted_data table
    5. Update status to 'completed' (or 'failed' if any step aborts)

    Args:
        doc_id (UUID): The primary key ID of the document in the database.
        file_path (str): The local system path to the PDF document.
        db_session (AsyncSession): The active SQLAlchemy async session.
    """
    logger.info(f"Initiating pipeline for document {doc_id}.")

    # 1. Update the document status in the database to 'processing'
    document = await _set_document_status(doc_id, "processing", db_session)
    if not document:
        logger.error(f"Pipeline aborted for document {doc_id}: Failed to set 'processing' status.")
        return

    # 2. Call the PDF text extraction function from Phase 2
    try:
        logger.info(f"Starting PDF extraction for document {doc_id} at {file_path}.")
        # Use asyncio.to_thread to prevent the blocking PDF parsing library from freezing the async event loop
        extracted_text = await asyncio.to_thread(extract_pdf_text, file_path)
        logger.info(f"Successfully extracted text from document {doc_id}.")
        
    except PDFReaderError as e:
        logger.error(f"PDF extraction explicitly failed for document {doc_id}. Reason: {e}")
        await _set_document_status(doc_id, "failed", db_session)
        return
    except Exception as e:
        logger.error(f"Unexpected catastrophic error during PDF extraction for document {doc_id}. Details: {e}", exc_info=True)
        await _set_document_status(doc_id, "failed", db_session)
        return

    # 3. Pass the extracted text to our async Gemini extraction function from Phase 3/4
    try:
        logger.info(f"Sending extracted text to Gemini LLM for structured analysis (Document {doc_id}).")
        structured_data = await run_structured_extraction(extracted_text)
        logger.info(f"Successfully received and parsed structured data from Gemini (Document {doc_id}).")
        
    except LLMExtractionError as e:
        logger.error(f"LLM API or Schema Parsing failed for document {doc_id}. Reason: {e}")
        await _set_document_status(doc_id, "failed", db_session)
        return
    except Exception as e:
        logger.error(f"Unexpected catastrophic error during LLM processing for document {doc_id}. Details: {e}", exc_info=True)
        await _set_document_status(doc_id, "failed", db_session)
        return

    # 4 & 5. Save the structured data and update status to 'completed'
    try:
        logger.info(f"Persisting structured extraction results to database for document {doc_id}.")
        
        # Instantiate the ExtractedData ORM model using the validated Pydantic properties
        extracted_data_record = ExtractedData(
            document_id=doc_id,
            party_name=structured_data.party_name,
            contract_value=structured_data.contract_value,
            payment_terms_days=structured_data.payment_terms_days,
            penalty_clause_exists=structured_data.penalty_clause_exists,
            governing_law=structured_data.governing_law,
            needs_review=structured_data.needs_review,  # Saved securely as per the Pydantic validator logic
            extracted_text=extracted_text
        )
        
        # Add to session
        db_session.add(extracted_data_record)
        
        # We can update the document status in the same transaction
        document.status = "completed"
        
        # Commit the transaction
        await db_session.commit()
        logger.info(f"Pipeline completely successfully for document {doc_id}. Data saved and status marked 'completed'.")
        
    except Exception as e:
        logger.error(f"Database error while saving extracted data for document {doc_id}. Details: {e}", exc_info=True)
        # Rollback the failed transaction
        await db_session.rollback()
        # Mark document as failed in a new transaction
        await _set_document_status(doc_id, "failed", db_session)
