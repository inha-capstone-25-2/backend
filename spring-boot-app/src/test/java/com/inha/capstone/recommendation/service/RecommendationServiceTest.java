package com.inha.capstone.recommendation.service;

import com.inha.capstone.recommendation.dto.RecommendationItem;
import com.inha.capstone.recommendation.dto.RecommendationResponse;
import com.inha.capstone.recommendation.model.RecommendationLog;
import com.inha.capstone.recommendation.repository.RecommendationRepository;
import com.inha.capstone.recommendation.util.RuleBasedRecommender;
import com.inha.capstone.user.domain.User;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.test.util.ReflectionTestUtils;

import java.util.Collections;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.BDDMockito.given;
import static org.mockito.BDDMockito.then;

@ExtendWith(MockitoExtension.class)
class RecommendationServiceTest {

    @Mock
    private RuleBasedRecommender recommender;

    @Mock
    private RecommendationRepository recommendationRepository;

    @InjectMocks
    private RecommendationService recommendationService;

    @Nested
    class GetRecommendations {

        @Test
        void 추천_목록_조회_성공() {
            // given
            User user = User.builder().build();
            ReflectionTestUtils.setField(user, "id", 1L);

            RecommendationItem item = RecommendationItem.builder()
                    .paperId("paper1")
                    .totalScore(10.0)
                    .breakdown(RecommendationItem.ScoreBreakdown.builder()
                            .interestScore(5.0)
                            .popularityScore(3.0)
                            .recencyScore(1.0)
                            .personalizationScore(1.0)
                            .build())
                    .reasons(Collections.emptyList())
                    .build();

            given(recommender.recommend(any(User.class), anyInt(), anyInt()))
                    .willReturn(Collections.singletonList(item));

            // when
            RecommendationResponse response = recommendationService.getRecommendations(user, 10);

            // then
            assertThat(response).isNotNull();
            assertThat(response.totalCount()).isEqualTo(1);
            
            then(recommendationRepository).should().save(any(RecommendationLog.class));
        }
    }
}
