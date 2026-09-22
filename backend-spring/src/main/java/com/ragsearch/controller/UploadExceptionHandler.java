package com.ragsearch.controller;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.multipart.MaxUploadSizeExceededException;

import java.util.Map;

/**
 * 업로드 크기 초과(413)에 이유를 담아 돌려준다.
 * 기본 응답은 본문이 비어 있어서, 프론트가 이벤트를 하나도 못 받고 "업로드 중..." 에서 멈췄다.
 */
@RestControllerAdvice
public class UploadExceptionHandler {

    @Value("${spring.servlet.multipart.max-file-size}")
    private String maxFileSize;

    @ExceptionHandler(MaxUploadSizeExceededException.class)
    public ResponseEntity<Map<String, String>> handleTooLarge() {
        return ResponseEntity.status(HttpStatus.PAYLOAD_TOO_LARGE)
                .body(Map.of("message", maxFileSize + " 이하 파일만 올릴 수 있어요."));
    }
}
