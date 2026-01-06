package com.inha.capstone.recommendation.controller;

import com.inha.capstone.auth.security.UserPrincipal;
import com.inha.capstone.recommendation.dto.RecommendationEventCreateRequest;
import com.inha.capstone.recommendation.dto.RecommendationEventListResponse;
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
            @AuthenticationPrincipal UserPrincipal userPrincipal,
            @RequestBody RecommendationEventCreateRequest request
    ) {
        return ResponseEntity.status(HttpStatus.CREATED)
                .body(service.logEvent(userPrincipal.getUser(), request));
    }

    @GetMapping("/session/{sessionId}")
    public ResponseEntity<RecommendationEventListResponse> getSessionEvents(
            @AuthenticationPrincipal UserPrincipal userPrincipal,
            @PathVariable String sessionId,
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "50") int pageSize
    ) {
        return ResponseEntity.ok(service.getEventsBySession(sessionId, page, pageSize));
    }

    @GetMapping("/users/{userId}")
    public ResponseEntity<RecommendationEventListResponse> getUserEvents(
            @AuthenticationPrincipal UserPrincipal userPrincipal,
            @PathVariable Long userId,
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "50") int pageSize
    ) {
        return ResponseEntity.ok(service.getEventsByUser(userId, page, pageSize));
    }
}

