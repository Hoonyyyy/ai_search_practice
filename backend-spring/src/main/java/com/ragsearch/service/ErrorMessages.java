package com.ragsearch.service;

import java.net.ConnectException;
import java.net.SocketTimeoutException;

import org.springframework.web.client.HttpServerErrorException;
import org.springframework.web.client.ResourceAccessException;
import org.apache.catalina.connector.ClientAbortException;


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
        if (e instanceof ResourceAccessException rae) {
            // 같은 예외라도 원인이 다르다. 연결 자체가 안 됐거나 시간 초과면 "자는 중"이지만,
            // 연결된 뒤 응답 도중 끊긴 것(Premature EOF 등)은 서버 쪽 고장이라 기다려도 소용없다.
            Throwable cause = rae.getCause();
            return cause instanceof ConnectException
                    || cause instanceof SocketTimeoutException;
        }
        if (e instanceof HttpServerErrorException se) {
            int code = se.getStatusCode().value();
            return code == 502 || code == 503 || code == 504;
        }
        return false;        
    }

    /**
     * 사용자가 창을 닫거나 새로고침해 브라우저 연결이 끊긴 경우. 에러가 아니라 정상 행동이다.
     *
     * ClientAbortException 은 Tomcat 이 브라우저로 응답을 쓰다 실패할 때만 던진다.
     * Spring 의 DisconnectedClientHelper 는 "connection reset by peer" 같은 문구로도 판별하는데,
     * 그 문구는 FastAPI 연결이 끊길 때도 나온다 — 서버 고장을 "사용자가 떠남"으로 숨길 수 있어 쓰지 않는다.
     */
    public static boolean isClientGone(Throwable e) {
        for (Throwable t = e; t != null; t = t.getCause()) {
            if (t instanceof ClientAbortException) {
                return true;
            }
        }
        return false;
    }    
    
}
