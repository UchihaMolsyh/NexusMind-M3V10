"""
Document Tools — OCR, table extraction, document parsing.
"""
import re
import os
import logging
from typing import Dict, Any, List
from core.tool_registry import registry, ToolParam

logger = logging.getLogger("nexusmind.tools.doc")


@registry.tool(
    name="ocr_image",
    description="Extract text from an image using OCR. Falls back to basic pixel analysis if pytesseract is unavailable.",
    category="Document Processing",
    parameters=[
        ToolParam("image_path", "string", "Path to the image file"),
    ]
)
def ocr_image(image_path: str) -> Dict[str, Any]:
    if not os.path.exists(image_path):
        return {"error": f"File not found: {image_path}"}

    # Try pytesseract first
    try:
        import pytesseract
        from PIL import Image
        img = Image.open(image_path)
        text = pytesseract.image_to_string(img)
        return {
            "text": text,
            "method": "pytesseract",
            "image": image_path,
            "dimensions": f"{img.width}x{img.height}",
        }
    except ImportError:
        pass

    # Fallback: basic image info
    try:
        from PIL import Image
        img = Image.open(image_path)
        return {
            "text": "[OCR unavailable — install pytesseract for text extraction]",
            "method": "fallback",
            "image": image_path,
            "dimensions": f"{img.width}x{img.height}",
            "mode": img.mode,
            "format": img.format,
        }
    except ImportError:
        return {
            "text": "[PIL not available]",
            "method": "none",
            "image": image_path,
        }


@registry.tool(
    name="extract_table",
    description="Extract tables from HTML or structured text content.",
    category="Document Processing",
    parameters=[
        ToolParam("content", "string", "HTML or text content containing tables"),
        ToolParam("format", "string", "Output format: 'json', 'csv', or 'markdown'", required=False, default="json"),
    ]
)
def extract_table(content: str, format: str = "json") -> Dict[str, Any]:
    tables = []

    # Try HTML table extraction
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(content, "html.parser")
        html_tables = soup.find_all("table")

        for table in html_tables:
            rows = []
            for tr in table.find_all("tr"):
                cells = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
                if cells:
                    rows.append(cells)
            if rows:
                tables.append(rows)
    except ImportError:
        pass

    # Fallback: detect pipe-delimited or tab-delimited tables
    if not tables:
        lines = content.strip().split("\n")
        current_table = []
        for line in lines:
            if "|" in line and not line.strip().startswith("#"):
                cells = [c.strip() for c in line.split("|") if c.strip()]
                if cells and not all(c.replace("-", "").replace(":", "") == "" for c in cells):
                    current_table.append(cells)
            else:
                if current_table:
                    tables.append(current_table)
                    current_table = []
        if current_table:
            tables.append(current_table)

    if not tables:
        return {"tables": [], "count": 0, "message": "No tables found in content"}

    # Format output
    formatted = []
    for table in tables:
        if format == "csv":
            csv_str = "\n".join(",".join(f'"{c}"' for c in row) for row in table)
            formatted.append(csv_str)
        elif format == "markdown":
            if len(table) > 1:
                header = "| " + " | ".join(table[0]) + " |"
                separator = "| " + " | ".join("---" for _ in table[0]) + " |"
                rows = "\n".join("| " + " | ".join(row) + " |" for row in table[1:])
                formatted.append(f"{header}\n{separator}\n{rows}")
            else:
                formatted.append("| " + " | ".join(table[0]) + " |")
        else:
            # JSON
            if len(table) > 1:
                headers = table[0]
                records = [dict(zip(headers, row)) for row in table[1:]]
                formatted.append(records)
            else:
                formatted.append(table)

    return {"tables": formatted, "count": len(tables), "format": format}


@registry.tool(
    name="parse_document",
    description="Parse a document file (TXT, MD, HTML) into structured text chunks for processing.",
    category="Document Processing",
    parameters=[
        ToolParam("file_path", "string", "Path to the document file"),
        ToolParam("chunk_size", "integer", "Characters per chunk", required=False, default=1000),
    ]
)
def parse_document(file_path: str, chunk_size: int = 1000) -> Dict[str, Any]:
    if not os.path.exists(file_path):
        return {"error": f"File not found: {file_path}"}

    ext = os.path.splitext(file_path)[1].lower()

    try:
        if ext in [".txt", ".md", ".py", ".js", ".css", ".html", ".json", ".yaml", ".yml", ".csv"]:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        else:
            return {"error": f"Unsupported file type: {ext}. Supported: .txt, .md, .html, .py, .js, etc."}

    except Exception as e:
        return {"error": f"Failed to read file: {e}"}

    # Strip HTML tags if HTML file
    if ext == ".html":
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(content, "html.parser")
            for tag in soup(["script", "style"]):
                tag.decompose()
            content = soup.get_text(separator="\n", strip=True)
        except ImportError:
            content = re.sub(r"<[^>]+>", "", content)

    # Chunk the content
    chunks = []
    words = content.split()
    current_chunk = []
    current_len = 0

    for word in words:
        current_chunk.append(word)
        current_len += len(word) + 1
        if current_len >= chunk_size:
            chunks.append(" ".join(current_chunk))
            current_chunk = []
            current_len = 0

    if current_chunk:
        chunks.append(" ".join(current_chunk))

    return {
        "file": file_path,
        "extension": ext,
        "total_chars": len(content),
        "total_chunks": len(chunks),
        "chunk_size": chunk_size,
        "chunks": chunks[:20],  # Return first 20 chunks
        "preview": content[:500],
    }
