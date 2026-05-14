package com.ragchunker.server.chunk.storage;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.contains;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.ragchunker.server.chunk.domain.ChunkDocument;
import com.ragchunker.server.chunk.domain.ChunkItem;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.jdbc.core.namedparam.MapSqlParameterSource;
import org.springframework.jdbc.core.namedparam.NamedParameterJdbcTemplate;

class ChunkStorageRepositoryTests {

    private final NamedParameterJdbcTemplate jdbcTemplate = mock(NamedParameterJdbcTemplate.class);
    private final ChunkStorageRepository repository = new ChunkStorageRepository(jdbcTemplate, new ObjectMapper());

    @Test
    void insertStoresDocumentAndChunksWithGeneratedDatabaseIds() {
        when(jdbcTemplate.update(any(String.class), any(MapSqlParameterSource.class))).thenReturn(1);
        ChunkDocument document = new ChunkDocument(
                "demo",
                "Demo",
                "markdown",
                List.of(new ChunkItem(
                        "demo_chunk_0001",
                        "demo",
                        "Intro",
                        List.of("Demo", "Intro"),
                        2,
                        "Hello",
                        "Demo > Intro\n\nHello")));

        StoredChunkDocument stored = repository.insert(document);

        ArgumentCaptor<MapSqlParameterSource> documentParameters =
                ArgumentCaptor.forClass(MapSqlParameterSource.class);
        verify(jdbcTemplate).update(contains("INSERT INTO chunk_document"), documentParameters.capture());
        MapSqlParameterSource documentValues = documentParameters.getValue();
        assertThat(documentValues.getValue("id")).isEqualTo(stored.id());
        assertThat(documentValues.getValue("docId")).isEqualTo("demo");
        assertThat(documentValues.getValue("docTitle")).isEqualTo("Demo");
        assertThat(documentValues.getValue("sourceType")).isEqualTo("markdown");
        assertThat(documentValues.getValue("chunkCount")).isEqualTo(1);

        ArgumentCaptor<MapSqlParameterSource[]> chunkParameters =
                ArgumentCaptor.forClass(MapSqlParameterSource[].class);
        verify(jdbcTemplate).batchUpdate(contains("INSERT INTO chunk_item"), chunkParameters.capture());
        MapSqlParameterSource chunkValues = chunkParameters.getValue()[0];
        assertThat(chunkValues.getValue("documentId")).isEqualTo(stored.id());
        assertThat(chunkValues.getValue("chunkId")).isEqualTo("demo_chunk_0001");
        assertThat(chunkValues.getValue("docId")).isEqualTo("demo");
        assertThat(chunkValues.getValue("sequenceNumber")).isEqualTo(1);
        assertThat(chunkValues.getValue("sectionTitle")).isEqualTo("Intro");
        assertThat(chunkValues.getValue("sectionPathJson")).isEqualTo("[\"Demo\",\"Intro\"]");
        assertThat(chunkValues.getValue("level")).isEqualTo(2);
        assertThat(chunkValues.getValue("text")).isEqualTo("Hello");
        assertThat(chunkValues.getValue("retrievalText")).isEqualTo("Demo > Intro\n\nHello");

        assertThat(stored.docId()).isEqualTo("demo");
        assertThat(stored.chunkCount()).isEqualTo(1);
    }
}
