package com.inha.capstone.recommendation.service;

import com.inha.capstone.recommendation.dto.RecommendationItem;
import com.inha.capstone.recommendation.dto.RecommendationResponse;
import com.inha.capstone.recommendation.model.RecommendationLog;
import com.inha.capstone.recommendation.repository.RecommendationRepository;
import com.inha.capstone.recommendation.util.RuleBasedRecommender;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.UUID;

@Service
@RequiredArgsConstructor
public class RecommendationService {

    private final RuleBasedRecommender recommender;
    private final RecommendationRepository recommendationRepository;

    public RecommendationResponse getRecommendations(Long userId, int topK) {
        String sessionId = UUID.randomUUID().toString();

        List<RecommendationItem> items = recommender.recommend(userId, topK, 50);
        List<RecommendationItem> resultItems = new ArrayList<>();

        for (RecommendationItem item : items) {
            try {
                RecommendationLog logEntry = RecommendationLog.builder()
                        .sessionId(sessionId)
                        .userId(userId)
                        .paperId(item.paperId())
                        .recommendationType("rule_based")
                        .score(item.totalScore())
                        .features(Map.of(
                                "interest", item.breakdown().interestScore(),
                                "popularity", item.breakdown().popularityScore(),
                                "recency", item.breakdown().recencyScore(),
                                "personalization", item.breakdown().personalizationScore()
                        ))
                        .context(Map.of("reasons", item.reasons()))
                        .wasClicked(false)
                        .recommendedAt(LocalDateTime.now())
                        .build();

                recommendationRepository.save(logEntry);

                resultItems.add(item.withRecommendationId(logEntry.getId()));
            } catch (Exception e) {
            }
        }

        return new RecommendationResponse(
                userId,
                sessionId,
                "rule_based",
                resultItems,
                resultItems.size(),
                LocalDateTime.now().toString()
        );
    }
}
