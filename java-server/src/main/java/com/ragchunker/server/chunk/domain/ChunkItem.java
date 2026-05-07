package com.ragchunker.server.chunk.domain;

import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.List;
import java.util.Objects;

/**
 * Java-side representation of a validated chunk item.
 */
public record ChunkItem(
        @JsonProperty("chunk_id")
        String chunkId,
        @JsonProperty("doc_id")
        String docId,
        @JsonProperty("section_title")
        String sectionTitle,
        @JsonProperty("section_path")
        List<String> sectionPath,
        @JsonProperty("level")
        int level,
        @JsonProperty("text")
        String text,
        @JsonProperty("retrieval_text")
        String retrievalText) {

    public ChunkItem {
        Objects.requireNonNull(chunkId, "chunkId must not be null.");
        Objects.requireNonNull(docId, "docId must not be null.");
        Objects.requireNonNull(sectionTitle, "sectionTitle must not be null.");
        sectionPath = List.copyOf(Objects.requireNonNull(sectionPath, "sectionPath must not be null."));
        Objects.requireNonNull(text, "text must not be null.");
        Objects.requireNonNull(retrievalText, "retrievalText must not be null.");
    }
}
