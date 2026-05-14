package com.ragchunker.server.chunk.validation;

import java.util.Objects;

/**
 * Field-level Chunk JSON validation error.
 */
public record ChunkValidationError(String field, String message) {

    public ChunkValidationError {
        Objects.requireNonNull(field, "field must not be null.");
        Objects.requireNonNull(message, "message must not be null.");
    }

    public String format() {
        return field + " " + message;
    }
}
