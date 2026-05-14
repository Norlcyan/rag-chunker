package com.ragchunker.server.chunk.storage;

import com.ragchunker.server.chunk.domain.ChunkDocument;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * Transaction boundary for storing one validated ChunkDocument and its chunks.
 */
@Service
public class ChunkStorageService {

    private final ChunkStorageRepository chunkStorageRepository;

    public ChunkStorageService(ChunkStorageRepository chunkStorageRepository) {
        this.chunkStorageRepository = chunkStorageRepository;
    }

    /**
     * Store the document row and all chunk rows in one transaction.
     */
    @Transactional
    public StoredChunkDocument store(ChunkDocument document) {
        return chunkStorageRepository.insert(document);
    }
}
