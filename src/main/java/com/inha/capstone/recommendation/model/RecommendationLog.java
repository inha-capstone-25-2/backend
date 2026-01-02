package com.inha.capstone.recommendation.model;

import lombok.AccessLevel;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;
import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.mapping.Document;
import org.springframework.data.mongodb.core.mapping.Field;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;

@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
@AllArgsConstructor(access = AccessLevel.PRIVATE)
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
