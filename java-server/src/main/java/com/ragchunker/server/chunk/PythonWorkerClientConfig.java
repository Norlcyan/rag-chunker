package com.ragchunker.server.chunk;

import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.client.RestClient;

@Configuration
@EnableConfigurationProperties(PythonWorkerProperties.class)
public class PythonWorkerClientConfig {

    @Bean
    public RestClient pythonWorkerRestClient(RestClient.Builder builder, PythonWorkerProperties properties) {
        return builder.baseUrl(properties.baseUrl()).build();
    }
}
