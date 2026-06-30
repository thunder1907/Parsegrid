import json
import logging

from litellm import acompletion
from litellm.exceptions import AuthenticationError, Timeout, APIError

from models.schemas import ExtractedContract

logger = logging.getLogger(__name__)


class LLMExtractionError(Exception):
    """Base exception for LLM extraction failures."""
    pass


class ExtractionTimeoutError(LLMExtractionError):
    """Raised when the LLM API request times out."""
    pass


class ExtractionAuthError(LLMExtractionError):
    """Raised when authentication with the LLM API fails."""
    pass


class ExtractionParseError(LLMExtractionError):
    """Raised when the LLM response cannot be parsed into the expected JSON schema."""
    pass


async def run_structured_extraction(text: str) -> ExtractedContract:
    """
    Runs an asynchronous structured LLM extraction on the provided text using Gemini 2.5 Flash.

    Args:
        text (str): The raw text extracted from a document.

    Returns:
        ExtractedContract: A validated Pydantic object containing the extracted fields
                           and their corresponding confidence scores.

    Raises:
        ExtractionTimeoutError: If the API request times out.
        ExtractionAuthError: If authentication with the LLM provider fails.
        ExtractionParseError: If the response cannot be parsed or validation fails.
        LLMExtractionError: For general unforeseen errors.
    """
    messages = [
        {
            "role": "system",
            "content": (
                "You are an expert contract analyst. Extract the requested fields from the "
                "contract text. You must also output a confidence score between 0.0 and 1.0 "
                "for each extracted field based on how explicitly it was stated in the text."
            )
        },
        {
            "role": "user",
            "content": f"Extract details from the following contract text:\n\n{text}"
        }
    ]

    try:
        # Leverage litellm's native structured output enforcement by passing the Pydantic class
        response = await acompletion(
            model="gemini/gemini-2.5-flash",
            messages=messages,
            response_format=ExtractedContract,
            timeout=30.0  # Failsafe timeout parameter
        )

        raw_content = response.choices[0].message.content

        if not raw_content:
            raise ExtractionParseError("The LLM returned an empty content string.")

        # Parse the JSON string into the strictly typed Pydantic v2 model
        return ExtractedContract.model_validate_json(raw_content)

    except Timeout as e:
        logger.error(f"LLM extraction timed out: {e}")
        raise ExtractionTimeoutError("The LLM API request timed out.") from e

    except AuthenticationError as e:
        logger.error(f"LLM extraction authentication failed: {e}")
        raise ExtractionAuthError("Authentication with the LLM API failed. Please check your credentials.") from e

    except (json.JSONDecodeError, ValueError) as e:
        logger.error(f"Failed to parse or validate structured JSON response: {e}")
        raise ExtractionParseError(f"Failed to parse LLM response into the ExtractedContract schema: {e}") from e
        
    except APIError as e:
        logger.error(f"LLM API error occurred: {e}")
        raise LLMExtractionError(f"An LLM API error occurred: {e}") from e

    except Exception as e:
        logger.error(f"Unexpected error during structured extraction: {e}")
        raise LLMExtractionError(f"An unexpected extraction failure occurred: {e}") from e
