package com.ragchunker.server.chunk.domain;

import java.util.List;
import java.util.Objects;

/**
 * Java-side representation of a validated Chunk JSON document.
 */
public record ChunkDocument(
        String docId,
        String docTitle,
        String sourceType,
        List<ChunkItem> chunks) {

    public ChunkDocument {
        Objects.requireNonNull(docId, "docId must not be null.");
        Objects.requireNonNull(docTitle, "docTitle must not be null.");
        Objects.requireNonNull(sourceType, "sourceType must not be null.");
        chunks = List.copyOf(Objects.requireNonNull(chunks, "chunks must not be null."));
    }
}
