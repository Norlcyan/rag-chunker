package com.ragchunker.server.chunk.domain;

import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.List;
import java.util.Objects;

/**
 * Java-side representation of a validated Chunk JSON document.
 */
public record ChunkDocument(
        @JsonProperty("doc_id")
        String docId,
        @JsonProperty("doc_title")
        String docTitle,
        @JsonProperty("source_type")
        String sourceType,
        @JsonProperty("chunks")
        List<ChunkItem> chunks) {

    public ChunkDocument {
        Objects.requireNonNull(docId, "docId must not be null.");
        Objects.requireNonNull(docTitle, "docTitle must not be null.");
        Objects.requireNonNull(sourceType, "sourceType must not be null.");
        chunks = List.copyOf(Objects.requireNonNull(chunks, "chunks must not be null."));
    }
}
