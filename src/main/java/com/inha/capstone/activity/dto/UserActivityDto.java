package com.inha.capstone.activity.dto;

import lombok.Builder;

import java.time.LocalDateTime;
import java.util.Map;

@Builder
public record UserActivityDto(
    String id,
    Long userId,
    String doi,
    String activityType,
    Map<String, Object> metadata,
    LocalDateTime timestamp
) {}
