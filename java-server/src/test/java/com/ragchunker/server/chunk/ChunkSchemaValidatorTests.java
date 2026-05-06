package com.ragchunker.server.chunk;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.ragchunker.server.chunk.domain.ChunkDocument;
import org.junit.jupiter.api.Test;

class ChunkSchemaValidatorTests {

    private final ChunkSchemaValidator validator = new ChunkSchemaValidator(new ObjectMapper());

    @Test
    void validateAcceptsValidChunkResponse() {
        ChunkDocument document = validator.validateAndParseHttpSuccessResponse("""
                {
                  "status": "ok",
                  "doc_id": "demo",
                  "doc_title": "Demo",
                  "source_type": "markdown",
                  "chunks": [
                    {
                      "chunk_id": "demo_chunk_0001",
                      "doc_id": "demo",
                      "section_title": "__preamble__",
                      "section_path": ["Demo", "__preamble__"],
                      "level": 0,
                      "text": "Intro",
                      "retrieval_text": "Demo > __preamble__\\n\\nIntro"
                    },
                    {
                      "chunk_id": "demo_chunk_0002",
                      "doc_id": "demo",
                      "section_title": "Details",
                      "section_path": ["Demo", "Overview", "Details"],
                      "level": 3,
                      "text": "Body",
                      "retrieval_text": "Demo > Overview > Details\\n\\nBody"
                    }
                  ]
                }
                """);

        assertThat(document.docId()).isEqualTo("demo");
        assertThat(document.docTitle()).isEqualTo("Demo");
        assertThat(document.sourceType()).isEqualTo("markdown");
        assertThat(document.chunks()).hasSize(2);
        assertThat(document.chunks().get(0).sectionTitle()).isEqualTo("__preamble__");
        assertThat(document.chunks().get(1).sectionPath()).containsExactly("Demo", "Overview", "Details");
        assertThat(document.chunks().get(1).retrievalText()).isEqualTo("Demo > Overview > Details\n\nBody");
    }

    @Test
    void validateRejectsInvalidChunkIdSequence() {
        assertThatThrownBy(() -> validator.validateAndParseHttpSuccessResponse("""
                {
                  "status": "ok",
                  "doc_id": "demo",
                  "doc_title": "Demo",
                  "source_type": "markdown",
                  "chunks": [
                    {
                      "chunk_id": "demo_chunk_0002",
                      "doc_id": "demo",
                      "section_title": "Intro",
                      "section_path": ["Demo", "Intro"],
                      "level": 2,
                      "text": "Hello",
                      "retrieval_text": "Demo > Intro\\n\\nHello"
                    }
                  ]
                }
                """))
                .isInstanceOf(ChunkSchemaValidationException.class)
                .hasMessageContaining("chunk_id must be demo_chunk_0001");
    }

    @Test
    void validateRejectsInvalidRetrievalText() {
        assertThatThrownBy(() -> validator.validateAndParseHttpSuccessResponse("""
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
                      "retrieval_text": "wrong"
                    }
                  ]
                }
                """))
                .isInstanceOf(ChunkSchemaValidationException.class)
                .hasMessageContaining("retrieval_text");
    }

    @Test
    void validateRejectsInvalidPreamblePath() {
        assertThatThrownBy(() -> validator.validateAndParseHttpSuccessResponse("""
                {
                  "status": "ok",
                  "doc_id": "demo",
                  "doc_title": "Demo",
                  "source_type": "markdown",
                  "chunks": [
                    {
                      "chunk_id": "demo_chunk_0001",
                      "doc_id": "demo",
                      "section_title": "__preamble__",
                      "section_path": ["Demo", "Intro"],
                      "level": 0,
                      "text": "Hello",
                      "retrieval_text": "Demo > Intro\\n\\nHello"
                    }
                  ]
                }
                """))
                .isInstanceOf(ChunkSchemaValidationException.class)
                .hasMessageContaining("level 0 chunk section_path");
    }
}
