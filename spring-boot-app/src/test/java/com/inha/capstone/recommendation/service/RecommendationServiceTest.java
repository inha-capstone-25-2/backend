package com.inha.capstone.recommendation.service;

import com.inha.capstone.recommendation.dto.RecommendationItem;
import com.inha.capstone.recommendation.dto.RecommendationResponse;
import com.inha.capstone.recommendation.model.RecommendationLog;
import com.inha.capstone.recommendation.repository.RecommendationRepository;
import com.inha.capstone.recommendation.util.RuleBasedRecommender;
import com.inha.capstone.user.domain.User;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.util.Collections;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class RecommendationServiceTest {

    @Mock
    private RuleBasedRecommender recommender;

    @Mock
    private RecommendationRepository recommendationRepository;

    @InjectMocks
    private RecommendationService recommendationService;

    @Test
    void getRecommendations_shouldReturnResponse_whenUserProvided() {
        // Given
        User user = User.builder().build();
        user.setId(1L);

        RecommendationItem item = RecommendationItem.builder()
                .paperId("paper1")
                .totalScore(10.0)
                .breakdown(RecommendationItem.ScoreBreakdown.builder().interestScore(5.0).build())
                .reasons(Collections.emptyList())
                .build();

        when(recommender.recommend(any(User.class), anyInt(), anyInt()))
                .thenReturn(Collections.singletonList(item));

        // When
        RecommendationResponse response = recommendationService.getRecommendations(user, 10);

        // Then
        assertNotNull(response);
        assertEquals(1, response.totalCount());
        verify(recommendationRepository).save(any(RecommendationLog.class));
    }
}
