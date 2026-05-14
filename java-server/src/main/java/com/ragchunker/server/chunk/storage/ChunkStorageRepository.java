package com.ragchunker.server.chunk.storage;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.ragchunker.server.chunk.domain.ChunkDocument;
import com.ragchunker.server.chunk.domain.ChunkItem;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;
import org.springframework.jdbc.core.namedparam.MapSqlParameterSource;
import org.springframework.jdbc.core.namedparam.NamedParameterJdbcTemplate;
import org.springframework.stereotype.Repository;

/**
 * JDBC persistence for validated Chunk JSON documents.
 */
@Repository
public class ChunkStorageRepository {

    private static final String INSERT_DOCUMENT_SQL = """
            INSERT INTO chunk_document (
                id,
                doc_id,
                doc_title,
                source_type,
                chunk_count
            ) VALUES (
                :id,
                :docId,
                :docTitle,
                :sourceType,
                :chunkCount
            )
            """;

    private static final String INSERT_CHUNK_SQL = """
            INSERT INTO chunk_item (
                id,
                document_id,
                chunk_id,
                doc_id,
                sequence_number,
                section_title,
                section_path_json,
                `level`,
                `text`,
                retrieval_text
            ) VALUES (
                :id,
                :documentId,
                :chunkId,
                :docId,
                :sequenceNumber,
                :sectionTitle,
                :sectionPathJson,
                :level,
                :text,
                :retrievalText
            )
            """;

    private final NamedParameterJdbcTemplate jdbcTemplate;
    private final ObjectMapper objectMapper;

    public ChunkStorageRepository(NamedParameterJdbcTemplate jdbcTemplate, ObjectMapper objectMapper) {
        this.jdbcTemplate = jdbcTemplate;
        this.objectMapper = objectMapper;
    }

    /**
     * Insert one upload as a new database document record, even when doc_id repeats.
     */
    public StoredChunkDocument insert(ChunkDocument document) {
        String documentDatabaseId = newDatabaseId();
        jdbcTemplate.update(INSERT_DOCUMENT_SQL, documentParameters(documentDatabaseId, document));
        insertChunks(documentDatabaseId, document.chunks());
        return new StoredChunkDocument(documentDatabaseId, document.docId(), document.chunks().size());
    }

    private MapSqlParameterSource documentParameters(String documentDatabaseId, ChunkDocument document) {
        return new MapSqlParameterSource()
                .addValue("id", documentDatabaseId)
                .addValue("docId", document.docId())
                .addValue("docTitle", document.docTitle())
                .addValue("sourceType", document.sourceType())
                .addValue("chunkCount", document.chunks().size());
    }

    private void insertChunks(String documentDatabaseId, List<ChunkItem> chunks) {
        if (chunks.isEmpty()) {
            return;
        }

        List<MapSqlParameterSource> parameters = new ArrayList<>(chunks.size());
        for (int index = 0; index < chunks.size(); index++) {
            ChunkItem chunk = chunks.get(index);
            parameters.add(chunkParameters(documentDatabaseId, chunk, index + 1));
        }
        jdbcTemplate.batchUpdate(INSERT_CHUNK_SQL, parameters.toArray(MapSqlParameterSource[]::new));
    }

    private MapSqlParameterSource chunkParameters(String documentDatabaseId, ChunkItem chunk, int sequenceNumber) {
        return new MapSqlParameterSource()
                .addValue("id", newDatabaseId())
                .addValue("documentId", documentDatabaseId)
                .addValue("chunkId", chunk.chunkId())
                .addValue("docId", chunk.docId())
                .addValue("sequenceNumber", sequenceNumber)
                .addValue("sectionTitle", chunk.sectionTitle())
                .addValue("sectionPathJson", sectionPathJson(chunk))
                .addValue("level", chunk.level())
                .addValue("text", chunk.text())
                .addValue("retrievalText", chunk.retrievalText());
    }

    private String sectionPathJson(ChunkItem chunk) {
        try {
            return objectMapper.writeValueAsString(chunk.sectionPath());
        } catch (JsonProcessingException ex) {
            throw new ChunkStorageException("Failed to serialize section_path.", ex);
        }
    }

    private String newDatabaseId() {
        return UUID.randomUUID().toString();
    }
}
