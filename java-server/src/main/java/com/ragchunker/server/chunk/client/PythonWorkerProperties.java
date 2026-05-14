package com.ragchunker.server.chunk.client;

import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "rag-chunker.python-worker")
public record PythonWorkerProperties(String baseUrl) {
}
