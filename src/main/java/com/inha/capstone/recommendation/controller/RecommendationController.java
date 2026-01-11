package com.inha.capstone.recommendation.controller;

import com.inha.capstone.auth.security.JwtAuthenticationToken;
import com.inha.capstone.common.exception.CustomException;
import com.inha.capstone.common.exception.ErrorCode;
import com.inha.capstone.recommendation.dto.RecommendationResponse;
import com.inha.capstone.recommendation.service.RecommendationService;
import com.inha.capstone.user.domain.User;
import com.inha.capstone.user.repository.UserRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/recommendations")
@RequiredArgsConstructor
public class RecommendationController {

    private final RecommendationService recommendationService;
    private final UserRepository userRepository;

    @GetMapping
    public ResponseEntity<RecommendationResponse> getRecommendations(
            @AuthenticationPrincipal JwtAuthenticationToken authentication,
            @RequestParam(defaultValue = "10") int topK
    ) {
        User user = findUserById(authentication.getUserId());
        return ResponseEntity.ok(recommendationService.getRecommendations(user, topK));
    }

    private User findUserById(Long userId) {
        return userRepository.findById(userId)
                .orElseThrow(() -> new CustomException(ErrorCode.USER_NOT_FOUND));
    }
}
