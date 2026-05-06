package com.ragchunker.server.chunk;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.charset.StandardCharsets;
import java.util.Map;
import org.springframework.core.io.ByteArrayResource;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.MultiValueMap;
import org.springframework.util.StreamUtils;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;
import org.springframework.web.multipart.MultipartFile;

/**
 * Client for the Python FastAPI chunking endpoint.
 */
@Service
public class PythonChunkClient {

    private final RestClient pythonWorkerRestClient;
    private final ObjectMapper objectMapper;
    private final ChunkSchemaValidator chunkSchemaValidator;

    public PythonChunkClient(
            RestClient pythonWorkerRestClient,
            ObjectMapper objectMapper,
            ChunkSchemaValidator chunkSchemaValidator) {
        this.pythonWorkerRestClient = pythonWorkerRestClient;
        this.objectMapper = objectMapper;
        this.chunkSchemaValidator = chunkSchemaValidator;
    }

    public ResponseEntity<String> chunk(MultipartFile file, String sourceType) {
        MultiValueMap<String, Object> body = new LinkedMultiValueMap<>();
        body.add("file", toResource(file));
        body.add("source_type", sourceType);

        try {
            return pythonWorkerRestClient.post()
                    .uri("/v1/chunk")
                    .contentType(MediaType.MULTIPART_FORM_DATA)
                    .body(body)
                    .exchange((request, response) -> {
                        String responseBody = StreamUtils.copyToString(response.getBody(), StandardCharsets.UTF_8);
                        if (response.getStatusCode().is2xxSuccessful()) {
                            chunkSchemaValidator.validateHttpSuccessResponse(responseBody);
                        }
                        HttpHeaders headers = new HttpHeaders();
                        MediaType contentType = response.getHeaders().getContentType();
                        headers.setContentType(contentType == null ? MediaType.APPLICATION_JSON : contentType);
                        return ResponseEntity.status(response.getStatusCode()).headers(headers).body(responseBody);
                    });
        } catch (RestClientException | UncheckedIOException | ChunkSchemaValidationException ex) {
            return errorResponse("Python worker request failed: " + ex.getMessage());
        }
    }

    private MultipartFileResource toResource(MultipartFile file) {
        try {
            return new MultipartFileResource(file.getBytes(), file.getOriginalFilename());
        } catch (IOException ex) {
            throw new UncheckedIOException(ex);
        }
    }

    private ResponseEntity<String> errorResponse(String message) {
        try {
            String body = objectMapper.writeValueAsString(Map.of("status", "error", "error", message));
            return ResponseEntity.status(HttpStatus.BAD_GATEWAY)
                    .contentType(MediaType.APPLICATION_JSON)
                    .body(body);
        } catch (JsonProcessingException ex) {
            throw new IllegalStateException("Failed to serialize error response.", ex);
        }
    }

    private static final class MultipartFileResource extends ByteArrayResource {

        private final String filename;

        private MultipartFileResource(byte[] byteArray, String filename) {
            super(byteArray);
            this.filename = filename;
        }

        @Override
        public String getFilename() {
            return filename;
        }
    }
}
