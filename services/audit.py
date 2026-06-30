import hashlib
import json
import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from models.database import AsyncSessionLocal, AuditLog

logger = logging.getLogger(__name__)


async def write_audit_entry(
    doc_id: UUID,
    event_type: str,
    model_used: str,
    input_text: str,
    output_data: dict,
    db_session: AsyncSession
) -> None:
    """
    Writes a secure, independent audit log entry for a document processing event.
    
    This function instantly calculates an SHA256 hash of the input text, captures exact
    millisecond timestamps, and creates the audit entry. It executes within an entirely
    independent database transaction using AsyncSessionLocal so that even if the primary
    document/extraction data insertion experiences a collision or rollback, the audit
    trail persists accurately.

    Args:
        doc_id (UUID): The UUID of the document.
        event_type (str): The event type (e.g., 'extraction_success', 'validation_failure').
        model_used (str): The AI model utilized.
        input_text (str): The raw input text processed.
        output_data (dict): The output payload.
        db_session (AsyncSession): The parent request session (intentionally bypassed here for isolation).
    """
    try:
        # Calculate SHA256 hash of the input text to verify historical document state
        input_hash = hashlib.sha256(input_text.encode('utf-8')).hexdigest()
        
        # Capture the exact timestamp down to the millisecond
        current_time = datetime.now(timezone.utc)
        
        # Stringify the raw data payload into a valid JSON dictionary format.
        # We serialize to string and back to dict to ensure default stringifiers (like for UUIDs/dates)
        # run correctly before SQLAlchemy saves it to the JSON column.
        json_payload = json.loads(json.dumps(output_data, default=str))

        # Wrap the execution layer inside an independent database transaction block
        # using a fresh session to ensure the audit log commits regardless of the main transaction
        async with AsyncSessionLocal() as isolated_session:
            audit_record = AuditLog(
                doc_id=doc_id,
                event_type=event_type,
                model_used=model_used,
                input_hash=input_hash,
                output_json=json_payload,
                timestamp=current_time
            )
            isolated_session.add(audit_record)
            await isolated_session.commit()
            
        logger.info(f"Independent audit log successfully created for document {doc_id} (Event: {event_type}).")
        
    except Exception as e:
        logger.critical(f"Failed to write secure audit log entry for document {doc_id}: {e}", exc_info=True)
