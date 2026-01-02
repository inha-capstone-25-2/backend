package com.inha.capstone.recommendation.service;

import com.inha.capstone.recommendation.dto.RecommendationEventCreateRequest;
import com.inha.capstone.recommendation.dto.RecommendationEventListResponse;
import com.inha.capstone.recommendation.dto.RecommendationEventResponse;
import com.inha.capstone.recommendation.model.RecommendationEvent;
import com.inha.capstone.recommendation.repository.RecommendationEventRepository;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageImpl;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;

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

    @Nested
    class 로그_이벤트 {

        @Test
        void 이벤트_로깅_성공() {
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
    }

    @Nested
    class 세션별_이벤트_조회 {

        @Test
        void 세션별_이벤트_조회_성공() {
            // given
            String sessionId = "sess-1";
            RecommendationEvent event = RecommendationEvent.builder().sessionId(sessionId).build();
            Page<RecommendationEvent> page = new PageImpl<>(List.of(event), PageRequest.of(0, 10), 1);
            given(repository.findBySessionId(any(), any(Pageable.class))).willReturn(page);

            // when
            RecommendationEventListResponse response = service.getEventsBySession(sessionId, 1, 10);

            // then
            assertThat(response.items()).hasSize(1);
            assertThat(response.total()).isEqualTo(1);
        }
    }
}
