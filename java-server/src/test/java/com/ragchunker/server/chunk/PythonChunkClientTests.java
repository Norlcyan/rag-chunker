package com.ragchunker.server.chunk;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.client.ExpectedCount.once;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.header;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.method;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.requestTo;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withBadRequest;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withSuccess;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.test.web.client.MockRestServiceServer;
import org.springframework.web.client.RestClient;

class PythonChunkClientTests {

    @Test
    void chunkReturnsSuccessfulPythonWorkerResponse() throws Exception {
        RestClient.Builder builder = RestClient.builder().baseUrl("http://127.0.0.1:8000");
        MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
        ObjectMapper objectMapper = new ObjectMapper();
        PythonChunkClient client = new PythonChunkClient(
                builder.build(), objectMapper, new ChunkSchemaValidator(objectMapper));
        MockMultipartFile file = new MockMultipartFile(
                "file",
                "demo.md",
                "text/markdown",
                "# Demo\n\n## Intro\nHello\n".getBytes());

        server.expect(once(), requestTo("http://127.0.0.1:8000/v1/chunk"))
                .andExpect(method(HttpMethod.POST))
                .andExpect(header(HttpHeaders.CONTENT_TYPE, org.hamcrest.Matchers.startsWith("multipart/form-data")))
                .andRespond(withSuccess("""
                        {
                          "status": "ok",
                          "doc_id": "demo",
                          "doc_title": "Demo",
                          "source_type": "markdown",
                          "chunks": [
                            {
                              "chunk_id": "demo_chunk_0001",
                              "doc_id": "demo",
                              "section_title": "Intro",
                              "section_path": ["Demo", "Intro"],
                              "level": 2,
                              "text": "Hello",
                              "retrieval_text": "Demo > Intro\\n\\nHello"
                            }
                          ]
                        }
                        """, MediaType.APPLICATION_JSON));

        ResponseEntity<String> response = client.chunk(file, "markdown");

        assertThat(response.getStatusCode().is2xxSuccessful()).isTrue();
        assertThat(response.getHeaders().getContentType()).isEqualTo(MediaType.APPLICATION_JSON);
        assertThat(objectMapper.readTree(response.getBody()).get("status").asText()).isEqualTo("ok");
        server.verify();
    }

    @Test
    void chunkForwardsPythonWorkerErrorResponse() {
        RestClient.Builder builder = RestClient.builder().baseUrl("http://127.0.0.1:8000");
        MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
        ObjectMapper objectMapper = new ObjectMapper();
        PythonChunkClient client = new PythonChunkClient(
                builder.build(), objectMapper, new ChunkSchemaValidator(objectMapper));
        MockMultipartFile file = new MockMultipartFile("file", "demo.txt", "text/plain", "text".getBytes());

        server.expect(once(), requestTo("http://127.0.0.1:8000/v1/chunk"))
                .andExpect(method(HttpMethod.POST))
                .andRespond(withBadRequest().body("{\"status\":\"error\",\"error\":\"Unsupported input type: .txt\"}")
                        .contentType(MediaType.APPLICATION_JSON));

        ResponseEntity<String> response = client.chunk(file, "markdown");

        assertThat(response.getStatusCode().value()).isEqualTo(400);
        assertThat(response.getBody()).contains("Unsupported input type");
        server.verify();
    }

    @Test
    void chunkReturnsBadGatewayWhenSuccessfulPythonResponseViolatesSchema() {
        RestClient.Builder builder = RestClient.builder().baseUrl("http://127.0.0.1:8000");
        MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
        ObjectMapper objectMapper = new ObjectMapper();
        PythonChunkClient client = new PythonChunkClient(
                builder.build(), objectMapper, new ChunkSchemaValidator(objectMapper));
        MockMultipartFile file = new MockMultipartFile("file", "demo.md", "text/markdown", "# Demo\n".getBytes());

        server.expect(once(), requestTo("http://127.0.0.1:8000/v1/chunk"))
                .andExpect(method(HttpMethod.POST))
                .andRespond(withSuccess("{\"status\":\"ok\",\"doc_id\":\"demo\",\"chunks\":[]}", MediaType.APPLICATION_JSON));

        ResponseEntity<String> response = client.chunk(file, "markdown");

        assertThat(response.getStatusCode().value()).isEqualTo(502);
        assertThat(response.getBody()).contains("status", "error", "doc_title must be a string");
        server.verify();
    }
}
