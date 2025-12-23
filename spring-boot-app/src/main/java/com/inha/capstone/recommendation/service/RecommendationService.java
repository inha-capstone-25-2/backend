package com.inha.capstone.recommendation.service;

import com.inha.capstone.recommendation.dto.RecommendationItem;
import com.inha.capstone.recommendation.dto.RecommendationResponse;
import com.inha.capstone.recommendation.model.RecommendationLog;
import com.inha.capstone.recommendation.repository.RecommendationRepository;
import com.inha.capstone.recommendation.util.RuleBasedRecommender;
import com.inha.capstone.user.domain.User;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;
import java.util.UUID;

@Slf4j
@Service
@RequiredArgsConstructor
public class RecommendationService {
    private final RuleBasedRecommender recommender;
    private final RecommendationRepository recommendationRepository;

    @Transactional
    public RecommendationResponse getRecommendations(User user, int topK) {
        String sessionId = UUID.randomUUID().toString();
        
        List<RecommendationItem> items = recommender.recommend(user, topK, 50);
        List<RecommendationItem> resultItems = new java.util.ArrayList<>();

        // Log recommendations
        for (RecommendationItem item : items) {
            RecommendationLog logEntry = RecommendationLog.builder()
                    .sessionId(sessionId)
                    .userId(user.getId())
                    .paperId(item.paperId())
                    .recommendationType("rule_based")
                    .score(item.totalScore())
                    .features(Map.of(
                            "interest", item.breakdown().interestScore(),
                            "popularity", item.breakdown().popularityScore()
                            // Add others
                    ))
                    .context(Map.of("reasons", item.reasons()))
                    .wasClicked(false)
                    .recommendedAt(LocalDateTime.now())
                    .build();
            
            recommendationRepository.save(logEntry);
            
            // Add to result list with populated ID
            resultItems.add(item.withRecommendationId(logEntry.getId()));
        }
        
        return RecommendationResponse.builder()
                .userId(user.getId())
                .sessionId(sessionId)
                .recommendationType("rule_based")
                .recommendations(resultItems)
                .totalCount(resultItems.size())
                .timestamp(LocalDateTime.now().toString())
                .build();
    }
}
