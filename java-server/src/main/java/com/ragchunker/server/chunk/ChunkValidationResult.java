package com.ragchunker.server.chunk;

import com.ragchunker.server.chunk.domain.ChunkDocument;
import java.util.List;
import java.util.Objects;

/**
 * Strict Chunk JSON validation result with all collected errors.
 */
public record ChunkValidationResult(
        boolean valid,
        ChunkDocument document,
        List<ChunkValidationError> errors) {

    public ChunkValidationResult {
        errors = List.copyOf(Objects.requireNonNull(errors, "errors must not be null."));
        if (valid && document == null) {
            throw new IllegalArgumentException("document must not be null when validation is valid.");
        }
        if (valid && !errors.isEmpty()) {
            throw new IllegalArgumentException("errors must be empty when validation is valid.");
        }
        if (!valid && errors.isEmpty()) {
            throw new IllegalArgumentException("errors must not be empty when validation is invalid.");
        }
        if (!valid && document != null) {
            throw new IllegalArgumentException("document must be null when validation is invalid.");
        }
    }

    public static ChunkValidationResult valid(ChunkDocument document) {
        return new ChunkValidationResult(true, document, List.of());
    }

    public static ChunkValidationResult invalid(List<ChunkValidationError> errors) {
        return new ChunkValidationResult(false, null, errors);
    }

    public String errorMessage() {
        return errors.stream()
                .map(ChunkValidationError::format)
                .reduce((left, right) -> left + "; " + right)
                .orElse("Chunk validation failed.");
    }
}
