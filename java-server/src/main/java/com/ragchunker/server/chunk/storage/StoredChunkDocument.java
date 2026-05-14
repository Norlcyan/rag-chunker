package com.ragchunker.server.chunk.storage;

import java.util.Objects;

/**
 * Database identity assigned to a stored ChunkDocument upload.
 */
public record StoredChunkDocument(String id, String docId, int chunkCount) {

    public StoredChunkDocument {
        Objects.requireNonNull(id, "id must not be null.");
        Objects.requireNonNull(docId, "docId must not be null.");
        if (chunkCount < 0) {
            throw new IllegalArgumentException("chunkCount must not be negative.");
        }
    }
}
