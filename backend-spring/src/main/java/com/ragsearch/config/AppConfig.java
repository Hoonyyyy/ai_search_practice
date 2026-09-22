package com.ragsearch.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.web.client.RestTemplate;

import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.LinkedBlockingQueue;
import java.util.concurrent.ThreadPoolExecutor;
import java.util.concurrent.TimeUnit;

@Configuration
public class AppConfig {
    private static final int MAX_CONCURRENT_UPLOADS = 3;

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

    /**
     * 업로드 전용 스레드풀 — 동시에 3개까지만 처리하고, 나머지는 줄을 서서 기다린다.
     * PDF 추출은 파일 크기의 약 6배 힙을 쓴다. 측정(힙 358MB): 10MB × 3개 동시 = 피크 162MB (45%).
     * 검색은 sseExecutor 를 따로 쓴다 — 업로드가 몰려도 검색이 줄 서지 않게.
     */
    @Bean
    public ThreadPoolExecutor uploadExecutor() {
        return new ThreadPoolExecutor(
                MAX_CONCURRENT_UPLOADS, MAX_CONCURRENT_UPLOADS,
                0L, TimeUnit.MILLISECONDS,
                new LinkedBlockingQueue<>());
    }
}
