package com.ragchunker.server.chunk;

import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RequestPart;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

/**
 * HTTP entrypoint for forwarding one uploaded document to the Python chunking worker.
 */
@RestController
public class ChunkController {

    private final PythonChunkClient pythonChunkClient;

    public ChunkController(PythonChunkClient pythonChunkClient) {
        this.pythonChunkClient = pythonChunkClient;
    }

    @PostMapping(value = "/v1/chunk", consumes = MediaType.MULTIPART_FORM_DATA_VALUE, produces = MediaType.APPLICATION_JSON_VALUE)
    public ResponseEntity<String> chunk(
            @RequestPart("file") MultipartFile file,
            @RequestParam(name = "source_type", defaultValue = "markdown") String sourceType) {
        return pythonChunkClient.chunk(file, sourceType);
    }
}
