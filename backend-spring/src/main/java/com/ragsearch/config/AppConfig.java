package com.ragsearch.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.web.client.RestTemplate;

import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

@Configuration
public class AppConfig {

    @Bean
    public RestTemplate restTemplate() {
        SimpleClientHttpRequestFactory factory = new SimpleClientHttpRequestFactory();
        factory.setConnectTimeout(10_000);
        factory.setReadTimeout(300_000); // 임베딩/LLM 스트리밍 최대 5분
        return new RestTemplate(factory);
    }

    /**
     * SseEmitter 비동기 처리를 위한 스레드풀.
     * SSE는 응답을 스트리밍하는 동안 스레드를 점유하므로 별도 풀 사용.
     */
    @Bean
    public ExecutorService sseExecutor() {
        return Executors.newCachedThreadPool();
    }
}
