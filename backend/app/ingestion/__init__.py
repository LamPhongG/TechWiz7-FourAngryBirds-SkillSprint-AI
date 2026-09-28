"""Document ingestion: file validation, PDF/DOCX/TXT/MD/CSV text extraction, chunking.

Owner: Chau Quoc Lam Phong. Output contract per chunk: {doc_id, chunk_id, section_id, heading, page, content}.
Entry point: `pipeline.process_file`. The chunker is a port of frontend `utils/chunker.js`; keep the two in
sync, because citations store `chunk_id` and both sides must number chunks the same way.
"""
