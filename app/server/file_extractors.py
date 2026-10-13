import os
import traceback
import zipfile
from xml.etree import ElementTree as ET

from logging_utils import log_message

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None


def extract_text_from_file(file_path):
    lower_name = file_path.lower()
    if lower_name.endswith(".txt") or lower_name.endswith(".md") or lower_name.endswith(".csv"):
        with open(file_path, "r", encoding="utf-8", errors="ignore") as text_file:
            return text_file.read()

    if lower_name.endswith(".pdf"):
        return extract_text_from_pdf(file_path)

    if lower_name.endswith(".docx"):
        return extract_text_from_docx(file_path)

    log_message(f"[extract] No extractor available for {os.path.basename(file_path)}")
    return ""


def extract_text_from_pdf(file_path):
    if PdfReader is None:
        log_message(f"[extract] PDF extractor dependency missing for {os.path.basename(file_path)}")
        return ""

    try:
        reader = PdfReader(file_path)
        pages = []
        for index, page in enumerate(reader.pages, start=1):
            try:
                page_text = page.extract_text() or ""
            except Exception:
                log_message(f"[extract] Failed to extract text from PDF page {index}")
                page_text = ""
            if page_text.strip():
                pages.append(page_text.strip())

        extracted = "\n\n".join(pages)
        log_message(
            f"[extract] PDF extracted {len(extracted)} chars from {os.path.basename(file_path)} "
            f"across {len(reader.pages)} pages"
        )
        return extracted
    except Exception:
        log_message(f"[extract] Failed to extract PDF text from {os.path.basename(file_path)}")
        log_message(traceback.format_exc())
        return ""


def extract_text_from_docx(file_path):
    try:
        with zipfile.ZipFile(file_path) as docx_file:
            xml_data = docx_file.read("word/document.xml")
        root = ET.fromstring(xml_data)
        namespaces = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        paragraphs = []
        for paragraph in root.findall(".//w:p", namespaces):
            parts = [node.text for node in paragraph.findall(".//w:t", namespaces) if node.text]
            text = "".join(parts).strip()
            if text:
                paragraphs.append(text)
        extracted = "\n".join(paragraphs)
        log_message(f"[extract] DOCX extracted {len(extracted)} chars from {os.path.basename(file_path)}")
        return extracted
    except Exception:
        log_message(f"[extract] Failed to extract DOCX text from {os.path.basename(file_path)}")
        log_message(traceback.format_exc())
        return ""
