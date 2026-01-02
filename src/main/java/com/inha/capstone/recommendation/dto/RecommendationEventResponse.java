package com.inha.capstone.recommendation.dto;

import com.inha.capstone.recommendation.model.RecommendationEvent;

import java.time.LocalDateTime;
import java.util.Map;

public record RecommendationEventResponse(
    String id,
    Long userId,
    String paperId,
    String activityType,
    String sessionId,
    Map<String, Object> metadata,
    LocalDateTime timestamp
) {
    public static RecommendationEventResponse from(RecommendationEvent event) {
        return new RecommendationEventResponse(
            event.getId(),
            event.getUserId(),
            event.getPaperId(),
            event.getActivityType(),
            event.getSessionId(),
            event.getMetadata(),
            event.getTimestamp()
        );
    }
}
