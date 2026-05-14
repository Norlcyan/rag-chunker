package com.ragchunker.server.chunk.client;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.client.ExpectedCount.once;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.header;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.method;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.requestTo;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withBadRequest;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withSuccess;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.ragchunker.server.chunk.validation.ChunkSchemaValidator;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.MediaType;
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

        PythonChunkResponse response = client.chunk(file, "markdown");

        assertThat(response.statusCode().is2xxSuccessful()).isTrue();
        assertThat(response.headers().getContentType()).isEqualTo(MediaType.APPLICATION_JSON);
        assertThat(objectMapper.readTree(response.body()).get("status").asText()).isEqualTo("ok");
        assertThat(response.validatedDocument()).isNotNull();
        assertThat(response.validatedDocument().docId()).isEqualTo("demo");
        assertThat(response.validatedDocument().chunks()).hasSize(1);
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

        PythonChunkResponse response = client.chunk(file, "markdown");

        assertThat(response.statusCode().value()).isEqualTo(400);
        assertThat(response.body()).contains("Unsupported input type");
        assertThat(response.validatedDocument()).isNull();
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

        PythonChunkResponse response = client.chunk(file, "markdown");

        assertThat(response.statusCode().value()).isEqualTo(502);
        assertThat(response.body()).contains("status", "error", "doc_title must be a string");
        assertThat(response.validatedDocument()).isNull();
        server.verify();
    }
}
