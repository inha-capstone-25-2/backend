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

    public record ScoreBreakdown(
        double interestScore,
        double popularityScore,
        double recencyScore,
        double personalizationScore
    ) {}

    public RecommendationItem withRecommendationId(String newId) {
        return new RecommendationItem(
            newId, paperId, title, summary, authors, categories, keywords, difficultyLevel,
            viewCount, bookmarkCount, updateDate, journalRef, totalScore, breakdown, reasons
        );
    }
}
