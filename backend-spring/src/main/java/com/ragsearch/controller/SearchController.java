package com.ragsearch.controller;

import com.ragsearch.dto.search.QueryRequestDto;
import com.ragsearch.service.SearchService;
import jakarta.servlet.http.HttpServletResponse;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

@RestController
@RequestMapping("/api/search")
@RequiredArgsConstructor
public class SearchController {

    private final SearchService searchService;

    @PostMapping(value = "/query", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public SseEmitter query(@RequestBody @Valid QueryRequestDto request,
                            @RequestHeader(value = "X-Session-Id", required = false) String sessionId,
                            HttpServletResponse response) {
        response.setHeader("X-Accel-Buffering", "no");
        response.setHeader("Cache-Control", "no-cache");
        return searchService.query(request.getQuestion(), request.getTopK(), sessionId);
    }
}
