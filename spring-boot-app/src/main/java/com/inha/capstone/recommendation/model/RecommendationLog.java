package com.inha.capstone.recommendation.model;

import lombok.Builder;
import lombok.Data;
import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.mapping.Document;
import org.springframework.data.mongodb.core.mapping.Field;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;

@Data
@Builder
@Document(collection = "paper_recommendations")
public class RecommendationLog {
    @Id
    private String id;
    
    @Field("session_id")
    private String sessionId;
    
    @Field("user_id")
    private Long userId;
    
    @Field("paper_id")
    private String paperId;
    
    @Field("recommendation_type")
    private String recommendationType;
    
    private Double score;
    
    private Map<String, Double> features; // interest_score, etc.
    
    private Map<String, Object> context; // reasons list inside
    
    @Field("was_clicked")
    private boolean wasClicked;
    
    @Field("recommended_at")
    private LocalDateTime recommendedAt;
}
