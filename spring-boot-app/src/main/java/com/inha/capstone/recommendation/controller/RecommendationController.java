package com.inha.capstone.recommendation.controller;

import com.inha.capstone.auth.security.UserPrincipal;
import com.inha.capstone.recommendation.dto.RecommendationResponse;
import com.inha.capstone.recommendation.service.RecommendationService;
import com.inha.capstone.user.domain.User;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/recommendations")
@RequiredArgsConstructor
public class RecommendationController {

    private final RecommendationService recommendationService;

    @GetMapping
    public ResponseEntity<RecommendationResponse> getRecommendations(
            @AuthenticationPrincipal UserPrincipal userPrincipal,
            @RequestParam(defaultValue = "10") int topK
    ) {
        if (userPrincipal == null) {
            // Recommendation usually requires user context
            return ResponseEntity.status(401).build(); 
        }
        
        if (topK <= 0 || topK > 100) {
            return ResponseEntity.badRequest().build();
        }
        
        User user = userPrincipal.getUser();
        return ResponseEntity.ok(recommendationService.getRecommendations(user, topK));
    }
}
