package com.inha.capstone.recommendation.service;

import com.inha.capstone.recommendation.dto.RecommendationEventCreateRequest;
import com.inha.capstone.recommendation.dto.RecommendationEventListResponse;
import com.inha.capstone.recommendation.dto.RecommendationEventResponse;
import com.inha.capstone.recommendation.model.RecommendationEvent;
import com.inha.capstone.recommendation.repository.RecommendationEventRepository;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.data.domain.Pageable;

import java.util.Collections;
import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.BDDMockito.given;
import static org.mockito.BDDMockito.then;

@ExtendWith(MockitoExtension.class)
class RecommendationEventServiceTest {

    @Mock
    private RecommendationEventRepository repository;

    @InjectMocks
    private RecommendationEventService service;

    @Test
    @DisplayName("이벤트 로깅 성공")
    void logEvent_Success() {
        // given
        RecommendationEventCreateRequest request = new RecommendationEventCreateRequest(
                1L,
                "p123",
                "CLICK",
                "sess-1",
                Map.of("duration", 10)
        );

        RecommendationEvent savedEvent = RecommendationEvent.builder()
                .id("evt-1")
                .userId(1L)
                .paperId("p123")
                .activityType("CLICK")
                .sessionId("sess-1")
                .build();

        given(repository.save(any(RecommendationEvent.class))).willReturn(savedEvent);

        // when
        RecommendationEventResponse response = service.logEvent(request);

        // then
        assertThat(response.id()).isEqualTo("evt-1");
        assertThat(response.userId()).isEqualTo(1L);
        then(repository).should().save(any(RecommendationEvent.class));
    }

    @Test
    @DisplayName("세션별 이벤트 조회")
    void getEventsBySession() {
        // given
        String sessionId = "sess-1";
        RecommendationEvent event = RecommendationEvent.builder().sessionId(sessionId).build();
        given(repository.findBySessionId(any(), any(Pageable.class))).willReturn(List.of(event));

        // when
        RecommendationEventListResponse response = service.getEventsBySession(sessionId, 1, 10);

        // then
        assertThat(response.items()).hasSize(1);
    }
}
