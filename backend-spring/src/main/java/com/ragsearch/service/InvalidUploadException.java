package com.ragsearch.service;

/**
 * 사용자에게 그대로 보여줘도 되는, 우리가 직접 쓴 업로드 거부 사유
 * 라이브러리가 던지는 IllegalArgumentException과 구분하기 위한 전용 타입
 */

public class InvalidUploadException extends RuntimeException{
    public InvalidUploadException(String message) {
        super(message);
    }
}
