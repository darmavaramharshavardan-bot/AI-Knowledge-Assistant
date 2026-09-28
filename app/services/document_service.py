from pathlib import Path
import re

from pypdf import PdfReader

from app.services.embedding_service import create_embedding
from app.models import Document, DocumentChunk


# ============================================================
# PDF PAGE EXTRACTION
# ============================================================

def extract_pages_from_pdf(file_path: str) -> list[dict]:
    """
    Extract text page-by-page from a PDF.

    Keeping pages separate allows us to preserve
    page-level metadata for every chunk.
    """

    reader = PdfReader(file_path)

    pages = []

    for page_number, page in enumerate(
        reader.pages,
        start=1
    ):
        text = page.extract_text()

        if not text:
            continue

        text = text.strip()

        if not text:
            continue

        pages.append(
            {
                "page_number": page_number,
                "text": text
            }
        )

    return pages


# ============================================================
# CLEAN EXTRACTED TEXT
# ============================================================

def clean_line(line: str) -> str:
    """
    Clean common PDF extraction artifacts.
    """

    line = line.strip()

    line = re.sub(
        r"\s+",
        " ",
        line
    )

    return line


def is_bad_section_candidate(line: str) -> bool:
    """
    Reject text that should not be treated
    as a section heading.
    """

    if not line:
        return True

    # PDF/model extraction artifacts
    if line.lower() in {
        "<eos>",
        "<bos>",
        "<pad>",
        "eos",
        "bos",
        "pad"
    }:
        return True

    # Figure/table labels
    if re.match(
        r"^(figure|fig\.|table)\s*\d+",
        line,
        re.IGNORECASE
    ):
        return True

    # Reference-style entries
    if line.startswith("["):
        return True

    # Too long to reasonably be a heading
    if len(line) > 120:
        return True

    # Too many words usually means paragraph text
    if len(line.split()) > 15:
        return True

    # Mathematical/table-like content
    if line.count("|") >= 2:
        return True

    return False


# ============================================================
# SECTION DETECTION
# ============================================================

def detect_section(text: str) -> str | None:
    """
    Detect a likely academic section heading.

    Examples:

        1 Introduction
        2 Background
        3 Model Architecture
        3.1 Encoder and Decoder Stacks
        3.2 Attention
        3.2.1 Scaled Dot-Product Attention

    Returns None when no reliable heading is found.
    """

    lines = text.splitlines()

    special_headings = {
        "abstract",
        "introduction",
        "conclusion",
        "references",
        "bibliography",
        "acknowledgements",
        "appendix"
    }

    for raw_line in lines:

        line = clean_line(raw_line)

        if is_bad_section_candidate(line):
            continue

        # ----------------------------------------------------
        # Numbered academic headings
        # ----------------------------------------------------

        numbered_heading = re.match(
            r"^(\d+(?:\.\d+)*)\s+(.+)$",
            line
        )

        if numbered_heading:

            title = numbered_heading.group(2).strip()

            if (
                len(title.split()) <= 15
                and not title.endswith(".")
            ):
                return line

        # ----------------------------------------------------
        # Special academic headings
        # ----------------------------------------------------

        if line.lower() in special_headings:
            return line

    return None


# ============================================================
# CAPTION DETECTION
# ============================================================

def looks_like_figure_caption(text: str) -> bool:
    """
    Determine whether the ENTIRE chunk looks like
    a figure caption.

    Important:
    A technical paragraph that merely mentions
    "Figure 2" should NOT become a figure_caption.
    """

    clean_text = clean_line(text)

    if not clean_text:
        return False

    # A real caption should normally be relatively short.
    words = clean_text.split()

    if len(words) > 60:
        return False

    # Caption normally starts with Figure/Fig.
    if re.match(
        r"^(figure|fig\.)\s*\d+",
        clean_text,
        re.IGNORECASE
    ):
        return True

    return False


def looks_like_table_caption(text: str) -> bool:
    """
    Determine whether the ENTIRE chunk looks like
    a table caption.
    """

    clean_text = clean_line(text)

    if not clean_text:
        return False

    words = clean_text.split()

    if len(words) > 60:
        return False

    if re.match(
        r"^table\s*\d+",
        clean_text,
        re.IGNORECASE
    ):
        return True

    return False


# ============================================================
# CHUNK TYPE DETECTION
# ============================================================

def detect_chunk_type(text: str) -> str:
    """
    Classify the chunk.

    Possible values:

        technical_content
        reference
        figure_caption
        table_caption
        heading
    """

    clean_text = text.strip()

    lower_text = clean_text.lower()

    # --------------------------------------------------------
    # REFERENCES
    # --------------------------------------------------------

    reference_indicators = [
        "arxiv preprint",
        "proceedings of",
        "international conference on learning representations",
        "bibliography"
    ]

    if (
        clean_text.startswith("[")
        or any(
            indicator in lower_text
            for indicator in reference_indicators
        )
    ):
        return "reference"

    # --------------------------------------------------------
    # FIGURE CAPTION
    # --------------------------------------------------------

    if looks_like_figure_caption(clean_text):
        return "figure_caption"

    # --------------------------------------------------------
    # TABLE CAPTION
    # --------------------------------------------------------

    if looks_like_table_caption(clean_text):
        return "table_caption"

    # --------------------------------------------------------
    # HEADING
    # --------------------------------------------------------

    if detect_section(clean_text) is not None:
        return "heading"

    # --------------------------------------------------------
    # NORMAL TECHNICAL CONTENT
    # --------------------------------------------------------

    return "technical_content"


# ============================================================
# TEXT CHUNKING
# ============================================================

def split_text(
    text: str,
    chunk_size: int = 500
) -> list[str]:
    """
    Split text into approximately equal
    word-based chunks.
    """

    words = text.split()

    chunks = []

    for i in range(
        0,
        len(words),
        chunk_size
    ):
        chunk = " ".join(
            words[i:i + chunk_size]
        )

        if chunk.strip():
            chunks.append(
                chunk.strip()
            )

    return chunks


# ============================================================
# PDF INGESTION
# ============================================================

def ingest_pdf(
    db,
    file_path: str,
    user_id: int
):
    """
    Read PDF, detect sections, preserve page metadata,
    create chunks, generate embeddings, and store them.
    """

    filename = Path(file_path).name

    # ========================================================
    # CREATE DOCUMENT
    # ========================================================

    document = Document(
        filename=filename,
        user_id=user_id
    )

    db.add(document)

    db.commit()

    db.refresh(document)

    # ========================================================
    # EXTRACT PAGES
    # ========================================================

    pages = extract_pages_from_pdf(
        file_path
    )

    total_chunks = 0

    # Remember the latest valid section.
    current_section = None

    # ========================================================
    # PROCESS EACH PAGE
    # ========================================================

    for page in pages:

        page_number = page["page_number"]

        page_text = page["text"]

        # ----------------------------------------------------
        # Detect a new section on this page
        # ----------------------------------------------------

        detected_section = detect_section(
            page_text
        )

        if detected_section:
            current_section = detected_section

        # ----------------------------------------------------
        # Split page into chunks
        # ----------------------------------------------------

        chunks = split_text(
            page_text,
            chunk_size=500
        )

        # ====================================================
        # PROCESS CHUNKS
        # ====================================================

        for chunk_text in chunks:

            # ------------------------------------------------
            # Detect content type
            # ------------------------------------------------

            chunk_type = detect_chunk_type(
                chunk_text
            )

            # ------------------------------------------------
            # Section handling
            # ------------------------------------------------

            chunk_section = (
                detect_section(chunk_text)
                or current_section
            )

            # ------------------------------------------------
            # Create embedding
            # ------------------------------------------------

            embedding = create_embedding(
                chunk_text
            )

            # ------------------------------------------------
            # Create database chunk
            # ------------------------------------------------

            chunk = DocumentChunk(
                document_id=document.id,
                content=chunk_text,
                embedding=embedding,
                page_number=page_number,
                section=chunk_section,
                chunk_type=chunk_type,
                source=filename
            )

            db.add(chunk)

            total_chunks += 1

    # ========================================================
    # SAVE
    # ========================================================

    db.commit()

    return {
        "document_id": document.id,
        "filename": filename,
        "chunks_created": total_chunks
    }