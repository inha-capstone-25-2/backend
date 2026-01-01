package com.inha.capstone.recommendation.controller;

import com.inha.capstone.auth.security.UserPrincipal;
import com.inha.capstone.recommendation.dto.RecommendationEventDto;
import com.inha.capstone.recommendation.service.RecommendationEventService;
import com.inha.capstone.user.domain.User;
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
    public ResponseEntity<RecommendationEventDto.Response> logEvent(
            @AuthenticationPrincipal UserPrincipal userPrincipal,
            @RequestBody RecommendationEventDto.CreateRequest request
    ) {
        if (userPrincipal == null) {
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED).build();
        }
        User user = userPrincipal.getUser();
        
        // Ensure user logs their own events only
        if (!user.getId().equals(request.getUserId())) {
            return ResponseEntity.status(HttpStatus.FORBIDDEN).build();
        }

        return ResponseEntity.status(HttpStatus.CREATED).body(service.logEvent(request));
    }

    @GetMapping("/session/{sessionId}")
    public ResponseEntity<RecommendationEventDto.EventListResponse> getSessionEvents(
            @AuthenticationPrincipal UserPrincipal userPrincipal,
            @PathVariable String sessionId,
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "50") int pageSize
    ) {
        if (userPrincipal == null) {
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED).build();
        }
        return ResponseEntity.ok(service.getEventsBySession(sessionId, page, pageSize));
    }

    @GetMapping("/users/{userId}")
    public ResponseEntity<RecommendationEventDto.EventListResponse> getUserEvents(
            @AuthenticationPrincipal UserPrincipal userPrincipal,
            @PathVariable Long userId,
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "50") int pageSize
    ) {
        if (userPrincipal == null) {
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED).build();
        }
        return ResponseEntity.ok(service.getEventsByUser(userId, page, pageSize));
    }
}
