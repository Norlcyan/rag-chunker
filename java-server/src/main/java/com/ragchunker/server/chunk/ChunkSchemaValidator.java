package com.ragchunker.server.chunk;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.ragchunker.server.chunk.domain.ChunkDocument;
import com.ragchunker.server.chunk.domain.ChunkItem;
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
     * Validate and parse the HTTP-wrapped successful response from Python /v1/chunk.
     */
    public ChunkValidationResult validateAndParseHttpSuccessResponse(String responseBody) {
        List<ChunkValidationError> errors = new ArrayList<>();
        JsonNode root = parseObject(responseBody, errors);
        if (root == null) {
            return ChunkValidationResult.invalid(errors);
        }

        String status = readText(root, "status", "status", true, errors);
        if (status != null && !OK_STATUS.equals(status)) {
            errors.add(new ChunkValidationError("status", "must be ok for successful Python responses."));
        }

        String docId = readText(root, "doc_id", "doc_id", true, errors);
        String docTitle = readText(root, "doc_title", "doc_title", true, errors);
        String sourceType = readText(root, "source_type", "source_type", true, errors);
        if (sourceType != null && !MARKDOWN_SOURCE_TYPE.equals(sourceType)) {
            errors.add(new ChunkValidationError("source_type", "must be markdown."));
        }

        JsonNode chunks = readArray(root, "chunks", "chunks", errors);
        List<ChunkItem> chunkItems = new ArrayList<>();
        if (chunks != null) {
            for (int index = 0; index < chunks.size(); index++) {
                ChunkItem chunk = validateChunk(chunks.get(index), index + 1, docId, docTitle, errors);
                if (chunk != null) {
                    chunkItems.add(chunk);
                }
            }
        }

        if (!errors.isEmpty()) {
            return ChunkValidationResult.invalid(errors);
        }
        return ChunkValidationResult.valid(new ChunkDocument(docId, docTitle, sourceType, chunkItems));
    }

    private JsonNode parseObject(String responseBody, List<ChunkValidationError> errors) {
        try {
            JsonNode root = objectMapper.readTree(responseBody);
            if (root == null || !root.isObject()) {
                errors.add(new ChunkValidationError("response_body", "must be a JSON object."));
                return null;
            }
            return root;
        } catch (JsonProcessingException ex) {
            errors.add(new ChunkValidationError("response_body", "must be valid JSON."));
            return null;
        }
    }

    private ChunkItem validateChunk(
            JsonNode chunk,
            int sequence,
            String docId,
            String docTitle,
            List<ChunkValidationError> errors) {
        String chunkPath = "chunks[" + (sequence - 1) + "]";
        if (chunk == null || !chunk.isObject()) {
            errors.add(new ChunkValidationError(chunkPath, "must be a JSON object."));
            return null;
        }

        String chunkId = readText(chunk, "chunk_id", chunkPath + ".chunk_id", true, errors);
        if (chunkId != null && docId != null) {
            String expectedChunkId = "%s_chunk_%04d".formatted(docId, sequence);
            if (!expectedChunkId.equals(chunkId)) {
                errors.add(new ChunkValidationError(chunkPath + ".chunk_id", "must be " + expectedChunkId + "."));
            }
        }

        String chunkDocId = readText(chunk, "doc_id", chunkPath + ".doc_id", true, errors);
        if (chunkDocId != null && docId != null && !docId.equals(chunkDocId)) {
            errors.add(new ChunkValidationError(chunkPath + ".doc_id", "must match top-level doc_id."));
        }

        String sectionTitle = readText(chunk, "section_title", chunkPath + ".section_title", true, errors);
        List<String> sectionPath = readStringArray(chunk, "section_path", chunkPath + ".section_path", errors);
        Integer level = readInt(chunk, "level", chunkPath + ".level", errors);
        String text = readText(chunk, "text", chunkPath + ".text", false, errors);
        String retrievalText = readText(chunk, "retrieval_text", chunkPath + ".retrieval_text", false, errors);

        validateSectionPath(sectionTitle, sectionPath, level, docTitle, chunkPath, errors);

        if (sectionPath != null && text != null && retrievalText != null) {
            String expectedRetrievalText = String.join(" > ", sectionPath) + "\n\n" + text;
            if (!expectedRetrievalText.equals(retrievalText)) {
                errors.add(new ChunkValidationError(
                        chunkPath + ".retrieval_text",
                        "must equal joined section_path plus text."));
            }
        }
        if (chunkId == null || chunkDocId == null || sectionTitle == null
                || sectionPath == null || level == null || text == null || retrievalText == null) {
            return null;
        }
        return new ChunkItem(chunkId, chunkDocId, sectionTitle, sectionPath, level, text, retrievalText);
    }

    private void validateSectionPath(
            String sectionTitle,
            List<String> sectionPath,
            Integer level,
            String docTitle,
            String chunkPath,
            List<ChunkValidationError> errors) {
        if (sectionPath == null || level == null) {
            return;
        }
        if (sectionPath.isEmpty()) {
            errors.add(new ChunkValidationError(chunkPath + ".section_path", "must not be empty."));
            return;
        }
        if (docTitle != null && !docTitle.equals(sectionPath.get(0))) {
            errors.add(new ChunkValidationError(chunkPath + ".section_path", "must start with doc_title."));
        }

        if (level == 0) {
            if (sectionTitle != null && !PREAMBLE_SECTION_TITLE.equals(sectionTitle)) {
                errors.add(new ChunkValidationError(
                        chunkPath + ".section_title",
                        "must be __preamble__ for level 0 chunks."));
            }
            if (sectionPath.size() != 2
                    || (docTitle != null && !docTitle.equals(sectionPath.get(0)))
                    || !PREAMBLE_SECTION_TITLE.equals(sectionPath.get(1))) {
                errors.add(new ChunkValidationError(
                        chunkPath + ".section_path",
                        "must be [doc_title, __preamble__] for level 0 chunks."));
            }
            return;
        }

        if (level != 2 && level != 3) {
            errors.add(new ChunkValidationError(chunkPath + ".level", "must be 0, 2, or 3 in the current MVP."));
        }
        if (sectionPath.size() != level) {
            errors.add(new ChunkValidationError(chunkPath + ".section_path", "size must match heading level."));
        }
        if (sectionTitle != null && !sectionTitle.equals(sectionPath.get(sectionPath.size() - 1))) {
            errors.add(new ChunkValidationError(chunkPath + ".section_path", "must end with section_title."));
        }
    }

    private String readText(
            JsonNode node,
            String fieldName,
            String fieldPath,
            boolean nonBlank,
            List<ChunkValidationError> errors) {
        JsonNode value = node.get(fieldName);
        if (value == null || !value.isTextual()) {
            errors.add(new ChunkValidationError(fieldPath, "must be a string."));
            return null;
        }
        String text = value.asText();
        if (nonBlank && text.isBlank()) {
            errors.add(new ChunkValidationError(fieldPath, "must not be blank."));
            return null;
        }
        return text;
    }

    private JsonNode readArray(
            JsonNode node,
            String fieldName,
            String fieldPath,
            List<ChunkValidationError> errors) {
        JsonNode value = node.get(fieldName);
        if (value == null || !value.isArray()) {
            errors.add(new ChunkValidationError(fieldPath, "must be an array."));
            return null;
        }
        return value;
    }

    private List<String> readStringArray(
            JsonNode node,
            String fieldName,
            String fieldPath,
            List<ChunkValidationError> errors) {
        JsonNode array = readArray(node, fieldName, fieldPath, errors);
        if (array == null) {
            return null;
        }
        List<String> values = new ArrayList<>();
        boolean valid = true;
        for (int index = 0; index < array.size(); index++) {
            JsonNode item = array.get(index);
            if (!item.isTextual() || item.asText().isBlank()) {
                errors.add(new ChunkValidationError(fieldPath + "[" + index + "]", "must be a non-blank string."));
                valid = false;
                continue;
            }
            values.add(item.asText());
        }
        return valid ? values : null;
    }

    private Integer readInt(
            JsonNode node,
            String fieldName,
            String fieldPath,
            List<ChunkValidationError> errors) {
        JsonNode value = node.get(fieldName);
        if (value == null || !value.isIntegralNumber() || !value.canConvertToInt()) {
            errors.add(new ChunkValidationError(fieldPath, "must be an integer."));
            return null;
        }
        return value.asInt();
    }
}
