package com.inha.capstone.recommendation.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

public record RecommendationInteractionRequest(
        @JsonProperty("paper_id") String paperId,
        @JsonProperty("recommendation_id") String recommendationId,
        @JsonProperty("action_type") String actionType,
        @JsonProperty("dwell_time") Double dwellTime
) {
    public RecommendationInteractionRequest {
        if (paperId == null || paperId.isBlank()) {
            throw new IllegalArgumentException("paper_id is required");
        }
        if (recommendationId == null || recommendationId.isBlank()) {
            throw new IllegalArgumentException("recommendation_id is required");
        }
        if (actionType == null) {
            actionType = "click";
        }
        if (!actionType.equals("click") && !actionType.equals("bookmark")) {
            throw new IllegalArgumentException("action_type must be click or bookmark");
        }
        if (dwellTime != null && (!Double.isFinite(dwellTime) || dwellTime < 0)) {
            throw new IllegalArgumentException("dwell_time must be nonnegative");
        }
    }
}
