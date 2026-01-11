package com.inha.capstone.recommendation.controller;

import com.inha.capstone.auth.security.JwtAuthenticationToken;
import com.inha.capstone.common.dto.PageResponse;
import com.inha.capstone.recommendation.dto.RecommendationEventCreateRequest;
import com.inha.capstone.recommendation.dto.RecommendationEventResponse;
import com.inha.capstone.recommendation.service.RecommendationEventService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/events")
@RequiredArgsConstructor
public class RecommendationEventController {

    private final RecommendationEventService service;

    @PostMapping
    public ResponseEntity<RecommendationEventResponse> logEvent(
            @AuthenticationPrincipal JwtAuthenticationToken authentication,
            @RequestBody RecommendationEventCreateRequest request
    ) {
        return ResponseEntity.status(HttpStatus.CREATED)
                .body(service.logEvent(authentication.getUserId(), request));
    }

    @GetMapping("/session/{sessionId}")
    public ResponseEntity<PageResponse<RecommendationEventResponse>> getSessionEvents(
            @AuthenticationPrincipal JwtAuthenticationToken authentication,
            @PathVariable String sessionId,
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "50") int pageSize
    ) {
        return ResponseEntity.ok(service.getEventsBySession(sessionId, page, pageSize));
    }

    @GetMapping("/users/{userId}")
    public ResponseEntity<PageResponse<RecommendationEventResponse>> getUserEvents(
            @AuthenticationPrincipal JwtAuthenticationToken authentication,
            @PathVariable Long userId,
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "50") int pageSize
    ) {
        return ResponseEntity.ok(service.getEventsByUser(userId, page, pageSize));
    }
}
