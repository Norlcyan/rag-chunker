-- Reference schema for the Java synchronous ChunkDocument storage MVP.
-- This file is documentation for local database preparation; Spring SQL init is disabled by default.

CREATE TABLE IF NOT EXISTS chunk_document (
    id VARCHAR(36) NOT NULL,
    doc_id VARCHAR(255) NOT NULL,
    doc_title VARCHAR(1024) NOT NULL,
    source_type VARCHAR(64) NOT NULL,
    chunk_count INT NOT NULL,
    created_at TIMESTAMP(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    PRIMARY KEY (id),
    KEY idx_chunk_document_doc_id (doc_id),
    KEY idx_chunk_document_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS chunk_item (
    id VARCHAR(36) NOT NULL,
    document_id VARCHAR(36) NOT NULL,
    chunk_id VARCHAR(512) NOT NULL,
    doc_id VARCHAR(255) NOT NULL,
    sequence_number INT NOT NULL,
    section_title VARCHAR(1024) NOT NULL,
    section_path_json TEXT NOT NULL,
    `level` INT NOT NULL,
    `text` LONGTEXT NOT NULL,
    retrieval_text LONGTEXT NOT NULL,
    created_at TIMESTAMP(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    PRIMARY KEY (id),
    KEY idx_chunk_item_document_sequence (document_id, sequence_number),
    KEY idx_chunk_item_doc_id (doc_id),
    KEY idx_chunk_item_chunk_id (chunk_id),
    CONSTRAINT fk_chunk_item_document
        FOREIGN KEY (document_id)
        REFERENCES chunk_document (id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
