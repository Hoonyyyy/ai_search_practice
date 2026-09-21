package com.ragsearch.service;

import org.springframework.web.client.HttpServerErrorException;
import org.springframework.web.client.ResourceAccessException;

/**
 * 예외를 사용자가 이해하고 행동할 수 있는 한 문장으로 바꾼다.
 * 예외 원문(내부 주소, DB 정보 등) 절대 화면에 내보내지 않는다 - 원인은 로그에 남긴다.
 */

public final class ErrorMessages {
    
    private ErrorMessages() {}  // 인스턴스를 만들 이유가 없는 유틸 클래스

    public static String forSearch(Exception e) {
        if (isAiServiceWakingUp(e)) {
            return "AI 서버가 잠에서 깨어나는 중이에요. 30초-1분 뒤 다시 질문해주세요.";
        }
        return "일시적인 문제로 답변을 만들지 못했어요. 잠시 후 다시 시도해 주세요.";            
    }

    public static String forUpload(Exception e) {
        if (isAiServiceWakingUp(e)) {
            return "AI 서버가 잠에서 깨어나는 중이에요. 30초-1분 뒤 다시 올려 주세요.";
        }
        return "일시적인 문제로 문서를 저장하지 못했어요. 잠시 후 다시 시도해 주세요.";
    }

    private static boolean isAiServiceWakingUp(Exception e) {
        if (e instanceof ResourceAccessException) {
            return true;        // 연결 거부, 타임 아웃
        }
        if (e instanceof HttpServerErrorException se) {
            int code = se.getStatusCode().value();
            return code == 502 || code == 503 || code == 504;
        }
        return false;        
    }
    
}
