package com.ragsearch.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.client.RestTemplate;

import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

@Configuration
public class AppConfig {

    /**
     * Python AI 서비스 HTTP 호출용 RestTemplate.
     * SSE 스트리밍 응답을 읽기 위해 타임아웃을 길게 설정.
     */
    @Bean
    public RestTemplate restTemplate() {
        return new RestTemplate();
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
