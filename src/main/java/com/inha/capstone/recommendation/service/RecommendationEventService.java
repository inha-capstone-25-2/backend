package com.inha.capstone.recommendation.service;

import com.inha.capstone.common.dto.PageResponse;
import com.inha.capstone.common.exception.CustomException;
import com.inha.capstone.common.exception.ErrorCode;
import com.inha.capstone.recommendation.dto.RecommendationEventCreateRequest;
import com.inha.capstone.recommendation.dto.RecommendationEventResponse;
import com.inha.capstone.recommendation.model.RecommendationEvent;
import com.inha.capstone.recommendation.repository.RecommendationEventRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Sort;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;

@Service
@RequiredArgsConstructor
public class RecommendationEventService {

    private final RecommendationEventRepository repository;

    public RecommendationEventResponse logEvent(Long userId, RecommendationEventCreateRequest request) {
        if (!userId.equals(request.userId())) {
            throw new CustomException(ErrorCode.FORBIDDEN);
        }

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

    public PageResponse<RecommendationEventResponse> getEventsBySession(String sessionId, int page, int pageSize) {
        PageRequest pageRequest = PageRequest.of(page - 1, pageSize, Sort.by(Sort.Direction.DESC, "timestamp"));
        Page<RecommendationEvent> eventPage = repository.findBySessionId(sessionId, pageRequest);
        return PageResponse.of(eventPage, RecommendationEventResponse::from);
    }

    public PageResponse<RecommendationEventResponse> getEventsByUser(Long userId, int page, int pageSize) {
        PageRequest pageRequest = PageRequest.of(page - 1, pageSize, Sort.by(Sort.Direction.DESC, "timestamp"));
        Page<RecommendationEvent> eventPage = repository.findByUserId(userId, pageRequest);
        return PageResponse.of(eventPage, RecommendationEventResponse::from);
    }
}
