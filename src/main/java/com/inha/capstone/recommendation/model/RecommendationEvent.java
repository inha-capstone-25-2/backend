package com.inha.capstone.recommendation.model;

import lombok.Builder;
import lombok.Getter;
import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.mapping.Document;

import java.time.LocalDateTime;
import java.util.Map;

@Document(collection = "recommendation_events")
@Getter
@Builder
public class RecommendationEvent {
    @Id
    private String id;
    private Long userId;
    private String paperId;
    private String activityType; // EXPOSE, CLICK, BOOKMARK, etc.
    private String sessionId;
    private Map<String, Object> metadata;
    private LocalDateTime timestamp;
}
