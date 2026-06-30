import hashlib
import re

import fitz  # PyMuPDF


class PDFReaderError(Exception):
    """Base exception for PDF reader module errors."""
    pass


class PDFCorruptedError(PDFReaderError):
    """Raised when a PDF file is corrupted, unreadable, or missing."""
    pass


class PDFEmptyError(PDFReaderError):
    """Raised when a PDF file contains no extractable text."""
    pass


class HashGenerationError(Exception):
    """Raised when file hash generation fails due to invalid input or unexpected errors."""
    pass


def extract_pdf_text(file_path: str) -> str:
    """
    Safely opens a PDF, iterates through all pages, extracts text,
    strips out excessive blank spacing, and merges it into a single clean string.

    Args:
        file_path (str): The path to the PDF file.

    Returns:
        str: The cleaned, merged text extracted from the PDF.

    Raises:
        PDFCorruptedError: If the PDF cannot be opened or is corrupted.
        PDFEmptyError: If the PDF contains no text.
    """
    try:
        doc = fitz.open(file_path)
    except Exception as e:
        raise PDFCorruptedError(
            f"Failed to open or read the PDF file at '{file_path}'. "
            f"It may be corrupted, missing, or unsupported. Details: {e}"
        ) from e

    extracted_text_parts = []

    try:
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text = page.get_text()
            if text:
                extracted_text_parts.append(text)
    except Exception as e:
        doc.close()
        raise PDFCorruptedError(
            f"An error occurred while reading pages of the PDF file '{file_path}'. Details: {e}"
        ) from e
    finally:
        # Ensure the document is closed safely
        doc.close()

    if not extracted_text_parts:
        raise PDFEmptyError(f"The PDF file at '{file_path}' contains no extractable text.")

    # Merge extracted text into a single string
    raw_text = "\n".join(extracted_text_parts)

    # Clean the text:
    # 1. Replace 3 or more consecutive newlines with exactly 2 newlines.
    clean_text = re.sub(r'\n{3,}', '\n\n', raw_text)
    # 2. Replace 2 or more consecutive horizontal spaces with a single space.
    clean_text = re.sub(r'[ \t]{2,}', ' ', clean_text)
    # 3. Strip leading/trailing whitespace
    clean_text = clean_text.strip()

    if not clean_text:
        raise PDFEmptyError(f"After cleaning, the PDF file at '{file_path}' contains only whitespace.")

    return clean_text


def generate_file_hash(file_bytes: bytes) -> str:
    """
    Calculates the SHA256 checksum of the file to detect duplicates.

    Args:
        file_bytes (bytes): The raw file bytes.

    Returns:
        str: The hexadecimal SHA256 checksum.

    Raises:
        HashGenerationError: If the input is not bytes or is empty.
    """
    if not isinstance(file_bytes, bytes):
        raise HashGenerationError(f"Expected bytes object, got '{type(file_bytes).__name__}'.")

    if not file_bytes:
        raise HashGenerationError("Cannot generate hash for empty file bytes.")

    try:
        sha256_hash = hashlib.sha256()
        sha256_hash.update(file_bytes)
        return sha256_hash.hexdigest()
    except Exception as e:
        raise HashGenerationError(
            f"An unexpected error occurred while calculating the SHA256 hash. Details: {e}"
        ) from e
