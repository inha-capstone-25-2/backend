package com.inha.capstone.recommendation.service;

import com.inha.capstone.recommendation.dto.RecommendationEventDto;
import com.inha.capstone.recommendation.model.RecommendationEvent;
import com.inha.capstone.recommendation.repository.RecommendationEventRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Sort;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.List;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
public class RecommendationEventService {

    private final RecommendationEventRepository repository;

    public RecommendationEventDto.Response logEvent(RecommendationEventDto.CreateRequest request) {
        RecommendationEvent event = RecommendationEvent.builder()
                .userId(request.getUserId())
                .paperId(request.getPaperId())
                .activityType(request.getActivityType())
                .sessionId(request.getSessionId())
                .metadata(request.getMetadata())
                .timestamp(LocalDateTime.now())
                .build();
        
        RecommendationEvent saved = repository.save(event);
        return RecommendationEventDto.Response.from(saved);
    }

    public RecommendationEventDto.EventListResponse getEventsBySession(String sessionId, int page, int pageSize) {
        PageRequest pageRequest = PageRequest.of(page - 1, pageSize, Sort.by(Sort.Direction.DESC, "timestamp"));
        List<RecommendationEvent> events = repository.findBySessionId(sessionId, pageRequest);
        
        List<RecommendationEventDto.Response> items = events.stream()
                .map(RecommendationEventDto.Response::from)
                .collect(Collectors.toList());
                
        // Note: Total count might be expensive in MongoDB if large, but for now we can just return size of page or implement count query
        // For simplicity matching the interface, we'll return items size as temporary total or implementation specific
        return new RecommendationEventDto.EventListResponse(items, items.size(), page, pageSize);
    }

    public RecommendationEventDto.EventListResponse getEventsByUser(Long userId, int page, int pageSize) {
        PageRequest pageRequest = PageRequest.of(page - 1, pageSize, Sort.by(Sort.Direction.DESC, "timestamp"));
        List<RecommendationEvent> events = repository.findByUserId(userId, pageRequest);

        List<RecommendationEventDto.Response> items = events.stream()
                .map(RecommendationEventDto.Response::from)
                .collect(Collectors.toList());

        return new RecommendationEventDto.EventListResponse(items, items.size(), page, pageSize);
    }
}
