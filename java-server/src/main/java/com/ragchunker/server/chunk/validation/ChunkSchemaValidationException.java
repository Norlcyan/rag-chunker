package com.ragchunker.server.chunk.validation;

public class ChunkSchemaValidationException extends RuntimeException {

    public ChunkSchemaValidationException(String message) {
        super(message);
    }

    public ChunkSchemaValidationException(String message, Throwable cause) {
        super(message, cause);
    }
}
