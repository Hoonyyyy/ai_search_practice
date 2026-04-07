package com.ragsearch.controller;

import com.ragsearch.dto.search.FeedbackRequestDto;
import com.ragsearch.dto.search.QueryRequestDto;
import com.ragsearch.service.SearchService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.util.Map;

@RestController
@RequestMapping("/api/search")
@RequiredArgsConstructor
public class SearchController {

    private final SearchService searchService;

    @PostMapping(value = "/query", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public SseEmitter query(@RequestBody @Valid QueryRequestDto request) {
        return searchService.query(request.getQuestion(), request.getTopK());
    }

    @PostMapping("/feedback")
    public ResponseEntity<Map<String, String>> feedback(@RequestBody @Valid FeedbackRequestDto request) {
        searchService.saveFeedback(request.getQueryId(), request.getScore());
        return ResponseEntity.ok(Map.of("message", "피드백 저장 완료"));
    }
}
