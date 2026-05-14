package com.ragchunker.server.chunk;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.ragchunker.server.chunk.domain.ChunkDocument;
import com.ragchunker.server.chunk.storage.ChunkStorageException;
import com.ragchunker.server.chunk.storage.ChunkStorageService;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.mock.web.MockMultipartFile;

class ChunkServiceTests {

    private final ObjectMapper objectMapper = new ObjectMapper();
    private final PythonChunkClient pythonChunkClient = mock(PythonChunkClient.class);
    private final ChunkStorageService chunkStorageService = mock(ChunkStorageService.class);
    private final ChunkService chunkService = new ChunkService(pythonChunkClient, chunkStorageService, objectMapper);

    @Test
    void chunkSavesValidatedDocumentAndPreservesSuccessfulPythonResponse() {
        MockMultipartFile file = markdownFile();
        ChunkDocument document = chunkDocument();
        String body = """
                {
                  "status": "ok",
                  "doc_id": "demo",
                  "doc_title": "Demo",
                  "source_type": "markdown",
                  "chunks": []
                }
                """;
        when(pythonChunkClient.chunk(file, "markdown"))
                .thenReturn(new PythonChunkResponse(HttpStatus.OK, jsonHeaders(), body, document));

        ResponseEntity<String> response = chunkService.chunk(file, "markdown");

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.OK);
        assertThat(response.getHeaders().getContentType()).isEqualTo(MediaType.APPLICATION_JSON);
        assertThat(response.getBody()).isEqualTo(body);
        verify(chunkStorageService).store(document);
    }

    @ParameterizedTest
    @ValueSource(ints = {400, 500})
    void chunkDoesNotSaveWhenPythonWorkerReturnsNon2xx(int statusCode) {
        MockMultipartFile file = markdownFile();
        HttpStatus status = HttpStatus.valueOf(statusCode);
        String body = "{\"status\":\"error\",\"error\":\"python failed\"}";
        when(pythonChunkClient.chunk(file, "markdown"))
                .thenReturn(new PythonChunkResponse(status, jsonHeaders(), body, null));

        ResponseEntity<String> response = chunkService.chunk(file, "markdown");

        assertThat(response.getStatusCode()).isEqualTo(status);
        assertThat(response.getBody()).isEqualTo(body);
        verifyNoInteractions(chunkStorageService);
    }

    @Test
    void chunkDoesNotSaveWhenSchemaValidationFailedInPythonClient() {
        MockMultipartFile file = markdownFile();
        String body = "{\"status\":\"error\",\"error\":\"doc_title must be a string\"}";
        when(pythonChunkClient.chunk(file, "markdown"))
                .thenReturn(new PythonChunkResponse(HttpStatus.BAD_GATEWAY, jsonHeaders(), body, null));

        ResponseEntity<String> response = chunkService.chunk(file, "markdown");

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.BAD_GATEWAY);
        assertThat(response.getBody()).isEqualTo(body);
        verifyNoInteractions(chunkStorageService);
    }

    @Test
    void chunkDoesNotSaveWhenSuccessfulPythonResponseHasNoValidatedDocument() throws Exception {
        MockMultipartFile file = markdownFile();
        when(pythonChunkClient.chunk(file, "markdown"))
                .thenReturn(new PythonChunkResponse(HttpStatus.OK, jsonHeaders(), "{\"status\":\"ok\"}", null));

        ResponseEntity<String> response = chunkService.chunk(file, "markdown");

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.BAD_GATEWAY);
        JsonNode errorBody = objectMapper.readTree(response.getBody());
        assertThat(errorBody.get("status").asText()).isEqualTo("error");
        assertThat(errorBody.get("error").asText()).contains("Chunk validation failed");
        verifyNoInteractions(chunkStorageService);
    }

    @Test
    void chunkReturnsInternalServerErrorJsonWhenStorageFails() throws Exception {
        MockMultipartFile file = markdownFile();
        ChunkDocument document = chunkDocument();
        when(pythonChunkClient.chunk(file, "markdown"))
                .thenReturn(new PythonChunkResponse(HttpStatus.OK, jsonHeaders(), "{\"status\":\"ok\"}", document));
        doThrow(new ChunkStorageException("database unavailable", new RuntimeException("connection refused")))
                .when(chunkStorageService)
                .store(document);

        ResponseEntity<String> response = chunkService.chunk(file, "markdown");

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.INTERNAL_SERVER_ERROR);
        assertThat(response.getHeaders().getContentType()).isEqualTo(MediaType.APPLICATION_JSON);
        JsonNode errorBody = objectMapper.readTree(response.getBody());
        assertThat(errorBody.get("status").asText()).isEqualTo("error");
        assertThat(errorBody.get("error").asText()).isNotBlank();
        verify(chunkStorageService).store(document);
    }

    private MockMultipartFile markdownFile() {
        return new MockMultipartFile(
                "file",
                "demo.md",
                "text/markdown",
                "# Demo\n\n## Intro\nHello\n".getBytes());
    }

    private ChunkDocument chunkDocument() {
        return new ChunkDocument("demo", "Demo", "markdown", List.of());
    }

    private HttpHeaders jsonHeaders() {
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        return headers;
    }
}
