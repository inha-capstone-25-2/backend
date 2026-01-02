package com.inha.capstone.activity.dto;

import com.inha.capstone.activity.model.UserActivity;

import java.time.LocalDateTime;
import java.util.Map;

public record UserActivityResponse(
    String id,
    Long userId,
    String doi,
    String activityType,
    Map<String, Object> metadata,
    LocalDateTime timestamp
) {
    public static UserActivityResponse from(UserActivity activity) {
        return new UserActivityResponse(
            activity.getId(),
            activity.getUserId(),
            activity.getDoi(),
            activity.getActivityType(),
            activity.getMetadata(),
            activity.getTimestamp()
        );
    }
}
