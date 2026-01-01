package com.inha.capstone.recommendation.dto;

import java.util.Map;

public record RecommendationEventCreateRequest(
    Long userId,
    String paperId,
    String activityType,
    String sessionId,
    Map<String, Object> metadata
) {}
