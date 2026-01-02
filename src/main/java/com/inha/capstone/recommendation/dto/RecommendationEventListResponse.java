package com.inha.capstone.recommendation.dto;

import java.util.List;

public record RecommendationEventListResponse(
    List<RecommendationEventResponse> items,
    long total,
    int page,
    int pageSize
) {}
