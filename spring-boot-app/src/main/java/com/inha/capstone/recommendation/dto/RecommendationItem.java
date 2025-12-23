package com.inha.capstone.recommendation.dto;

import com.inha.capstone.paper.model.Paper;
import lombok.Builder;

import java.util.List;

@Builder
public record RecommendationItem(
    String recommendationId,
    String paperId,
    String title,
    Paper.Summary summary,
    String authors,
    List<String> categories,
    List<String> keywords,
    String difficultyLevel,
    int viewCount,
    int bookmarkCount,
    String updateDate,
    String journalRef,
    double totalScore,
    ScoreBreakdown breakdown,
    List<String> reasons
) {
    // Setter needed? Records are immutable. 
    // If logic needs to set recommendationId after creation, it must use toBuilder() or create new instance.
    // However, in RecommendationService we did item.setRecommendationId(logEntry.getId());
    // This will break. We need to handle this.
    
    @Builder
    public record ScoreBreakdown(
        double interestScore,
        double popularityScore,
        double recencyScore,
        double personalizationScore
    ) {}
    
    // Helper to create a new record with updated recommendationId
    public RecommendationItem withRecommendationId(String newId) {
        return new RecommendationItem(
            newId, paperId, title, summary, authors, categories, keywords, difficultyLevel, 
            viewCount, bookmarkCount, updateDate, journalRef, totalScore, breakdown, reasons
        );
    }
}
