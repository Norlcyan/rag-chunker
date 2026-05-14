package com.ragchunker.server.chunk.client;

import com.ragchunker.server.chunk.domain.ChunkDocument;
import java.util.Objects;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatusCode;
import org.springframework.http.ResponseEntity;

/**
 * Response from Python Worker with the validated Java-side Chunk model when available.
 */
public record PythonChunkResponse(
        HttpStatusCode statusCode,
        HttpHeaders headers,
        String body,
        ChunkDocument validatedDocument) {

    public PythonChunkResponse {
        Objects.requireNonNull(statusCode, "statusCode must not be null.");
        Objects.requireNonNull(headers, "headers must not be null.");
        Objects.requireNonNull(body, "body must not be null.");
        HttpHeaders copiedHeaders = new HttpHeaders();
        copiedHeaders.putAll(headers);
        headers = HttpHeaders.readOnlyHttpHeaders(copiedHeaders);
    }

    public ResponseEntity<String> toResponseEntity() {
        return ResponseEntity.status(statusCode).headers(headers).body(body);
    }
}
