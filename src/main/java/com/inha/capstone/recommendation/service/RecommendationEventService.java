package com.inha.capstone.recommendation.service;

import com.inha.capstone.recommendation.dto.RecommendationEventCreateRequest;
import com.inha.capstone.recommendation.dto.RecommendationEventListResponse;
import com.inha.capstone.recommendation.dto.RecommendationEventResponse;
import com.inha.capstone.recommendation.model.RecommendationEvent;
import com.inha.capstone.recommendation.repository.RecommendationEventRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Sort;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.List;

@Service
@RequiredArgsConstructor
public class RecommendationEventService {

    private final RecommendationEventRepository repository;

    public RecommendationEventResponse logEvent(RecommendationEventCreateRequest request) {
        RecommendationEvent event = RecommendationEvent.builder()
                .userId(request.userId())
                .paperId(request.paperId())
                .activityType(request.activityType())
                .sessionId(request.sessionId())
                .metadata(request.metadata())
                .timestamp(LocalDateTime.now())
                .build();

        RecommendationEvent saved = repository.save(event);
        return RecommendationEventResponse.from(saved);
    }

    public RecommendationEventListResponse getEventsBySession(String sessionId, int page, int pageSize) {
        PageRequest pageRequest = PageRequest.of(page - 1, pageSize, Sort.by(Sort.Direction.DESC, "timestamp"));
        Page<RecommendationEvent> eventPage = repository.findBySessionId(sessionId, pageRequest);

        List<RecommendationEventResponse> items = eventPage.getContent().stream()
                .map(RecommendationEventResponse::from)
                .toList();

        return new RecommendationEventListResponse(items, eventPage.getTotalElements(), page, pageSize);
    }

    public RecommendationEventListResponse getEventsByUser(Long userId, int page, int pageSize) {
        PageRequest pageRequest = PageRequest.of(page - 1, pageSize, Sort.by(Sort.Direction.DESC, "timestamp"));
        Page<RecommendationEvent> eventPage = repository.findByUserId(userId, pageRequest);

        List<RecommendationEventResponse> items = eventPage.getContent().stream()
                .map(RecommendationEventResponse::from)
                .toList();

        return new RecommendationEventListResponse(items, eventPage.getTotalElements(), page, pageSize);
    }
}
