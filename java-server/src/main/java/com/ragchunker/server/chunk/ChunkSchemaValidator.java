package com.ragchunker.server.chunk;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.util.ArrayList;
import java.util.List;
import org.springframework.stereotype.Component;

/**
 * Validates the current MVP Chunk JSON contract returned by the Python worker.
 */
@Component
public class ChunkSchemaValidator {

    private static final String OK_STATUS = "ok";
    private static final String MARKDOWN_SOURCE_TYPE = "markdown";
    private static final String PREAMBLE_SECTION_TITLE = "__preamble__";

    private final ObjectMapper objectMapper;

    public ChunkSchemaValidator(ObjectMapper objectMapper) {
        this.objectMapper = objectMapper;
    }

    /**
     * Validate the HTTP-wrapped successful response from Python /v1/chunk.
     */
    public void validateHttpSuccessResponse(String responseBody) {
        JsonNode root = parseObject(responseBody);
        requireText(root, "status", true);
        if (!OK_STATUS.equals(root.get("status").asText())) {
            throw new ChunkSchemaValidationException("status must be ok for successful Python responses.");
        }

        String docId = requireText(root, "doc_id", true);
        String docTitle = requireText(root, "doc_title", true);
        String sourceType = requireText(root, "source_type", true);
        if (!MARKDOWN_SOURCE_TYPE.equals(sourceType)) {
            throw new ChunkSchemaValidationException("source_type must be markdown.");
        }

        JsonNode chunks = requireArray(root, "chunks");
        for (int index = 0; index < chunks.size(); index++) {
            validateChunk(chunks.get(index), index + 1, docId, docTitle);
        }
    }

    private JsonNode parseObject(String responseBody) {
        try {
            JsonNode root = objectMapper.readTree(responseBody);
            if (root == null || !root.isObject()) {
                throw new ChunkSchemaValidationException("response body must be a JSON object.");
            }
            return root;
        } catch (JsonProcessingException ex) {
            throw new ChunkSchemaValidationException("response body must be valid JSON.", ex);
        }
    }

    private void validateChunk(JsonNode chunk, int sequence, String docId, String docTitle) {
        if (chunk == null || !chunk.isObject()) {
            throw new ChunkSchemaValidationException("chunks[" + (sequence - 1) + "] must be a JSON object.");
        }

        String expectedChunkId = "%s_chunk_%04d".formatted(docId, sequence);
        String chunkId = requireText(chunk, "chunk_id", true);
        if (!expectedChunkId.equals(chunkId)) {
            throw new ChunkSchemaValidationException("chunk_id must be " + expectedChunkId + ".");
        }

        String chunkDocId = requireText(chunk, "doc_id", true);
        if (!docId.equals(chunkDocId)) {
            throw new ChunkSchemaValidationException("chunk doc_id must match top-level doc_id.");
        }

        String sectionTitle = requireText(chunk, "section_title", true);
        List<String> sectionPath = requireStringArray(chunk, "section_path");
        int level = requireInt(chunk, "level");
        String text = requireText(chunk, "text", false);
        String retrievalText = requireText(chunk, "retrieval_text", false);

        validateSectionPath(sectionTitle, sectionPath, level, docTitle);

        String expectedRetrievalText = String.join(" > ", sectionPath) + "\n\n" + text;
        if (!expectedRetrievalText.equals(retrievalText)) {
            throw new ChunkSchemaValidationException("retrieval_text must equal joined section_path plus text.");
        }
    }

    private void validateSectionPath(String sectionTitle, List<String> sectionPath, int level, String docTitle) {
        if (sectionPath.isEmpty()) {
            throw new ChunkSchemaValidationException("section_path must not be empty.");
        }
        if (!docTitle.equals(sectionPath.get(0))) {
            throw new ChunkSchemaValidationException("section_path must start with doc_title.");
        }

        if (level == 0) {
            if (!PREAMBLE_SECTION_TITLE.equals(sectionTitle)) {
                throw new ChunkSchemaValidationException("level 0 chunk section_title must be __preamble__.");
            }
            if (sectionPath.size() != 2
                    || !docTitle.equals(sectionPath.get(0))
                    || !PREAMBLE_SECTION_TITLE.equals(sectionPath.get(1))) {
                throw new ChunkSchemaValidationException("level 0 chunk section_path must be [doc_title, __preamble__].");
            }
            return;
        }

        if (level != 2 && level != 3) {
            throw new ChunkSchemaValidationException("current MVP only accepts chunk level 0, 2, or 3.");
        }
        if (sectionPath.size() != level) {
            throw new ChunkSchemaValidationException("section_path size must match heading level.");
        }
        if (!sectionTitle.equals(sectionPath.get(sectionPath.size() - 1))) {
            throw new ChunkSchemaValidationException("section_path must end with section_title.");
        }
    }

    private String requireText(JsonNode node, String fieldName, boolean nonBlank) {
        JsonNode value = node.get(fieldName);
        if (value == null || !value.isTextual()) {
            throw new ChunkSchemaValidationException(fieldName + " must be a string.");
        }
        String text = value.asText();
        if (nonBlank && text.isBlank()) {
            throw new ChunkSchemaValidationException(fieldName + " must not be blank.");
        }
        return text;
    }

    private JsonNode requireArray(JsonNode node, String fieldName) {
        JsonNode value = node.get(fieldName);
        if (value == null || !value.isArray()) {
            throw new ChunkSchemaValidationException(fieldName + " must be an array.");
        }
        return value;
    }

    private List<String> requireStringArray(JsonNode node, String fieldName) {
        JsonNode array = requireArray(node, fieldName);
        List<String> values = new ArrayList<>();
        for (JsonNode item : array) {
            if (!item.isTextual() || item.asText().isBlank()) {
                throw new ChunkSchemaValidationException(fieldName + " must contain non-blank strings.");
            }
            values.add(item.asText());
        }
        return values;
    }

    private int requireInt(JsonNode node, String fieldName) {
        JsonNode value = node.get(fieldName);
        if (value == null || !value.isIntegralNumber() || !value.canConvertToInt()) {
            throw new ChunkSchemaValidationException(fieldName + " must be an integer.");
        }
        return value.asInt();
    }
}
