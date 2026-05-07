package com.ragchunker.server.chunk.domain;

import java.util.List;
import java.util.Objects;

/**
 * Java-side representation of a validated chunk item.
 */
public record ChunkItem(
        String chunkId,
        String docId,
        String sectionTitle,
        List<String> sectionPath,
        int level,
        String text,
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
