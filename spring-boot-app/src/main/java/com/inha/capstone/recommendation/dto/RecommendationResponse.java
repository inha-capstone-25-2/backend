package com.inha.capstone.recommendation.dto;

import lombok.Builder;
import java.util.List;

@Builder
public record RecommendationResponse(
    Long userId,
    String sessionId,
    String recommendationType,
    List<RecommendationItem> recommendations,
    int totalCount,
    String timestamp
) {}
