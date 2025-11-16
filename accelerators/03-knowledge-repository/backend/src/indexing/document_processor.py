"""Document processing and chunking for knowledge repository."""

import hashlib
from pathlib import Path
from typing import List, Optional

from dataforge_common.logging import get_logger

logger = get_logger(__name__)


class DocumentChunk:
    """Represents a chunk of a document."""

    def __init__(
        self,
        content: str,
        metadata: dict,
        chunk_id: Optional[str] = None,
    ):
        """
        Initialize document chunk.

        Args:
            content: Chunk text content
            metadata: Chunk metadata (source, page, etc.)
            chunk_id: Unique chunk identifier
        """
        self.content = content
        self.metadata = metadata
        self.chunk_id = chunk_id or self._generate_id()

    def _generate_id(self) -> str:
        """Generate unique ID based on content hash."""
        content_hash = hashlib.md5(self.content.encode()).hexdigest()
        return f"chunk_{content_hash[:16]}"

    def to_dict(self) -> dict:
        """Convert chunk to dictionary."""
        return {
            "chunk_id": self.chunk_id,
            "content": self.content,
            "metadata": self.metadata,
        }


class DocumentProcessor:
    """
    Process documents for indexing.

    Handles:
    - Text extraction from various formats
    - Document chunking strategies
    - Metadata extraction

    Example:
        processor = DocumentProcessor(chunk_size=512, chunk_overlap=50)

        chunks = processor.process_file("./docs/guide.md")
        for chunk in chunks:
            print(chunk.content)
    """

    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        chunk_strategy: str = "recursive",
    ):
        """
        Initialize document processor.

        Args:
            chunk_size: Target size for each chunk (in characters)
            chunk_overlap: Overlap between chunks
            chunk_strategy: Chunking strategy ('fixed', 'recursive', 'semantic')
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.chunk_strategy = chunk_strategy
        self.logger = logger

    def process_file(self, file_path: str) -> List[DocumentChunk]:
        """
        Process a single file.

        Args:
            file_path: Path to file

        Returns:
            List of document chunks
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        self.logger.info("Processing file", path=str(file_path))

        # Extract text based on file type
        text = self._extract_text(file_path)

        # Extract metadata
        metadata = self._extract_metadata(file_path)

        # Chunk the text
        chunks = self._chunk_text(text, metadata)

        self.logger.info(
            "File processed",
            path=str(file_path),
            chunks=len(chunks),
        )

        return chunks

    def process_directory(
        self,
        directory: str,
        file_extensions: Optional[List[str]] = None,
        recursive: bool = True,
    ) -> List[DocumentChunk]:
        """
        Process all files in a directory.

        Args:
            directory: Directory path
            file_extensions: File extensions to process (default: ['.md', '.txt', '.py'])
            recursive: Process subdirectories

        Returns:
            List of all document chunks
        """
        directory = Path(directory)

        if file_extensions is None:
            file_extensions = [".md", ".txt", ".py", ".rst", ".json", ".yaml"]

        self.logger.info(
            "Processing directory",
            path=str(directory),
            extensions=file_extensions,
        )

        all_chunks = []

        # Find all matching files
        pattern = "**/*" if recursive else "*"
        for ext in file_extensions:
            for file_path in directory.glob(f"{pattern}{ext}"):
                if file_path.is_file():
                    try:
                        chunks = self.process_file(str(file_path))
                        all_chunks.extend(chunks)
                    except Exception as e:
                        self.logger.error(
                            "Failed to process file",
                            path=str(file_path),
                            error=str(e),
                        )

        self.logger.info(
            "Directory processing complete",
            total_chunks=len(all_chunks),
        )

        return all_chunks

    def _extract_text(self, file_path: Path) -> str:
        """Extract text from file based on extension."""
        ext = file_path.suffix.lower()

        if ext in [".txt", ".md", ".rst"]:
            # Plain text files
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()

        elif ext in [".py", ".js", ".java", ".cpp", ".c"]:
            # Code files
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()

        elif ext in [".json", ".yaml", ".yml"]:
            # Configuration files
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()

        else:
            self.logger.warning(
                "Unsupported file type, treating as text",
                extension=ext,
            )
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()

    def _extract_metadata(self, file_path: Path) -> dict:
        """Extract metadata from file."""
        return {
            "source": str(file_path),
            "filename": file_path.name,
            "extension": file_path.suffix,
            "size_bytes": file_path.stat().st_size,
        }

    def _chunk_text(self, text: str, metadata: dict) -> List[DocumentChunk]:
        """Chunk text using selected strategy."""
        if self.chunk_strategy == "fixed":
            return self._chunk_fixed(text, metadata)
        elif self.chunk_strategy == "recursive":
            return self._chunk_recursive(text, metadata)
        else:
            return self._chunk_fixed(text, metadata)

    def _chunk_fixed(self, text: str, metadata: dict) -> List[DocumentChunk]:
        """
        Fixed-size chunking with overlap.

        Simple strategy that splits text into fixed-size chunks.
        """
        chunks = []
        start = 0

        while start < len(text):
            end = start + self.chunk_size

            # Get chunk with overlap
            chunk_text = text[start:end]

            if chunk_text.strip():
                chunk_metadata = metadata.copy()
                chunk_metadata["chunk_index"] = len(chunks)
                chunk_metadata["start_char"] = start
                chunk_metadata["end_char"] = end

                chunks.append(DocumentChunk(chunk_text, chunk_metadata))

            # Move start position (with overlap)
            start = end - self.chunk_overlap

        return chunks

    def _chunk_recursive(self, text: str, metadata: dict) -> List[DocumentChunk]:
        """
        Recursive chunking that respects natural boundaries.

        Tries to split on:
        1. Paragraphs (double newline)
        2. Sentences (period + space)
        3. Fixed size (fallback)
        """
        chunks = []

        # Split on paragraphs first
        paragraphs = text.split("\n\n")

        current_chunk = ""
        chunk_index = 0

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            # If adding this paragraph would exceed chunk size
            if len(current_chunk) + len(para) > self.chunk_size:
                # Save current chunk if it's not empty
                if current_chunk.strip():
                    chunk_metadata = metadata.copy()
                    chunk_metadata["chunk_index"] = chunk_index
                    chunks.append(DocumentChunk(current_chunk, chunk_metadata))
                    chunk_index += 1

                # If paragraph itself is too large, split it
                if len(para) > self.chunk_size:
                    # Split on sentences
                    sentences = para.split(". ")
                    temp_chunk = ""

                    for sent in sentences:
                        if len(temp_chunk) + len(sent) > self.chunk_size:
                            if temp_chunk.strip():
                                chunk_metadata = metadata.copy()
                                chunk_metadata["chunk_index"] = chunk_index
                                chunks.append(DocumentChunk(temp_chunk, chunk_metadata))
                                chunk_index += 1
                            temp_chunk = sent
                        else:
                            temp_chunk += sent + ". "

                    current_chunk = temp_chunk
                else:
                    current_chunk = para
            else:
                current_chunk += "\n\n" + para if current_chunk else para

        # Add remaining chunk
        if current_chunk.strip():
            chunk_metadata = metadata.copy()
            chunk_metadata["chunk_index"] = chunk_index
            chunks.append(DocumentChunk(current_chunk, chunk_metadata))

        return chunks
