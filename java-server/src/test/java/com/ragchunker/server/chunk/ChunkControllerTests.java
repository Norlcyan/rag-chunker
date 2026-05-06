package com.ragchunker.server.chunk;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.multipart;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;
import org.springframework.web.multipart.MultipartFile;

class ChunkControllerTests {

    @Test
    void chunkForwardsMultipartRequestAndReturnsPythonResponse() throws Exception {
        PythonChunkClient pythonChunkClient = mock(PythonChunkClient.class);
        MockMvc mockMvc = MockMvcBuilders.standaloneSetup(new ChunkController(pythonChunkClient)).build();
        MockMultipartFile file = new MockMultipartFile(
                "file",
                "demo.md",
                "text/markdown",
                "# Demo\n\n## Intro\nHello\n".getBytes());

        when(pythonChunkClient.chunk(any(MultipartFile.class), eq("markdown")))
                .thenReturn(ResponseEntity.ok()
                        .contentType(MediaType.APPLICATION_JSON)
                        .body("{\"status\":\"ok\",\"doc_id\":\"demo\",\"chunks\":[]}"));

        mockMvc.perform(multipart("/v1/chunk").file(file).param("source_type", "markdown"))
                .andExpect(status().isOk())
                .andExpect(content().contentTypeCompatibleWith(MediaType.APPLICATION_JSON))
                .andExpect(content().json("{\"status\":\"ok\",\"doc_id\":\"demo\",\"chunks\":[]}"));
    }
}
