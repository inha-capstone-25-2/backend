package com.inha.capstone.recommendation.controller;

import com.inha.capstone.auth.security.JwtAuthenticationToken;
import com.inha.capstone.common.dto.ApiResponse;
import com.inha.capstone.common.dto.ErrorResponse;
import com.inha.capstone.recommendation.dto.RecommendationInteractionRequest;
import com.inha.capstone.recommendation.service.RecommendationAiClient;
import com.inha.capstone.recommendation.service.RecommendationAiClient.RecommendationAiException;
import jakarta.servlet.http.HttpServletResponse;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.CurrentSecurityContext;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.io.IOException;

@RestController
@RequestMapping("/api/recommendations")
@RequiredArgsConstructor
public class RecommendationAiController {
    private final RecommendationAiClient client;

    @GetMapping("/rl")
    public void recommendations(
            @CurrentSecurityContext(expression = "authentication") JwtAuthenticationToken authentication,
            @RequestParam(name = "base_paper_id", required = false) String basePaperId,
            @RequestParam(defaultValue = "6") int limit,
            @RequestParam(name = "candidate_k", defaultValue = "100") int candidateK,
            HttpServletResponse response
    ) throws IOException {
        if (limit < 1 || limit > 50 || candidateK < 10 || candidateK > 500) {
            throw new IllegalArgumentException("limit or candidate_k is out of range");
        }
        write(response, client.recommendations(authentication.getUserId(), basePaperId, limit, candidateK));
    }

    @PostMapping("/interactions")
    public void interaction(
            @CurrentSecurityContext(expression = "authentication") JwtAuthenticationToken authentication,
            @RequestBody RecommendationInteractionRequest request,
            HttpServletResponse response
    ) throws IOException {
        write(response, client.interaction(authentication.getUserId(), request));
    }

    @ExceptionHandler(RecommendationAiException.class)
    public ResponseEntity<ApiResponse<Void>> upstreamFailure() {
        return ResponseEntity.status(HttpStatus.BAD_GATEWAY)
                .body(ApiResponse.error(ErrorResponse.of("BAD_GATEWAY", "Recommendation service unavailable", 502)));
    }

    private void write(HttpServletResponse response, byte[] body) throws IOException {
        response.setContentType(MediaType.APPLICATION_JSON_VALUE);
        response.getOutputStream().write(body);
    }
}
