package com.ragchunker.server.chunk;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.ragchunker.server.chunk.domain.ChunkDocument;
import com.ragchunker.server.chunk.storage.ChunkStorageException;
import com.ragchunker.server.chunk.storage.ChunkStorageService;
import java.util.Map;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.dao.DataAccessException;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

/**
 * Orchestrates chunking, Java-side validation result handling, and synchronous storage.
 */
@Service
public class ChunkService {

    private static final Logger log = LoggerFactory.getLogger(ChunkService.class);

    private final PythonChunkClient pythonChunkClient;
    private final ChunkStorageService chunkStorageService;
    private final ObjectMapper objectMapper;

    public ChunkService(
            PythonChunkClient pythonChunkClient,
            ChunkStorageService chunkStorageService,
            ObjectMapper objectMapper) {
        this.pythonChunkClient = pythonChunkClient;
        this.chunkStorageService = chunkStorageService;
        this.objectMapper = objectMapper;
    }

    /**
     * Forward the upload to Python and persist only successful, validated Chunk JSON.
     */
    public ResponseEntity<String> chunk(MultipartFile file, String sourceType) {
        PythonChunkResponse pythonResponse = pythonChunkClient.chunk(file, sourceType);
        if (!pythonResponse.statusCode().is2xxSuccessful()) {
            return pythonResponse.toResponseEntity();
        }

        ChunkDocument document = pythonResponse.validatedDocument();
        if (document == null) {
            log.warn("Python worker returned 2xx but Java validation did not produce a ChunkDocument.");
            return errorResponse(HttpStatus.BAD_GATEWAY, "Chunk validation failed.");
        }

        try {
            chunkStorageService.store(document);
        } catch (DataAccessException | ChunkStorageException ex) {
            log.warn("Failed to persist chunk document doc_id={}: {}", document.docId(), ex.getMessage());
            log.debug("Chunk persistence failure detail.", ex);
            return errorResponse(HttpStatus.INTERNAL_SERVER_ERROR, "Chunk persistence failed.");
        }

        return pythonResponse.toResponseEntity();
    }

    private ResponseEntity<String> errorResponse(HttpStatus status, String message) {
        try {
            String body = objectMapper.writeValueAsString(Map.of("status", "error", "error", message));
            return ResponseEntity.status(status).contentType(MediaType.APPLICATION_JSON).body(body);
        } catch (JsonProcessingException ex) {
            throw new IllegalStateException("Failed to serialize error response.", ex);
        }
    }
}
