package com.inha.capstone.recommendation.dto;

import com.inha.capstone.recommendation.model.RecommendationEvent;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;

public class RecommendationEventDto {

    @Getter
    @NoArgsConstructor
    @AllArgsConstructor
    @Builder
    public static class CreateRequest {
        private Long userId;
        private String paperId;
        private String activityType;
        private String sessionId;
        private Map<String, Object> metadata;
    }

    @Getter
    @NoArgsConstructor
    @AllArgsConstructor
    @Builder
    public static class Response {
        private String id;
        private Long userId;
        private String paperId;
        private String activityType;
        private String sessionId;
        private Map<String, Object> metadata;
        private LocalDateTime timestamp;
        
        public static Response from(RecommendationEvent event) {
            return Response.builder()
                .id(event.getId())
                .userId(event.getUserId())
                .paperId(event.getPaperId())
                .activityType(event.getActivityType())
                .sessionId(event.getSessionId())
                .metadata(event.getMetadata())
                .timestamp(event.getTimestamp())
                .build();
        }
    }

    @Getter
    @AllArgsConstructor
    public static class EventListResponse {
        private List<Response> items;
        private int total;
        private int page;
        private int pageSize;
    }
}
