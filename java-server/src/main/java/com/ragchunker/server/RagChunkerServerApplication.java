package com.ragchunker.server;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/**
 * Java service entrypoint for rag-chunker.
 */
@SpringBootApplication
public class RagChunkerServerApplication {

    public static void main(String[] args) {
        SpringApplication.run(RagChunkerServerApplication.class, args);
    }
}
