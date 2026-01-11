package com.inha.capstone.activity.service;

import com.inha.capstone.activity.dto.UserActivityResponse;
import com.inha.capstone.activity.model.UserActivity;
import com.inha.capstone.activity.repository.ActivityRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Sort;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;

@Service
@RequiredArgsConstructor
public class ActivityService {

    private final ActivityRepository activityRepository;

    public void logActivity(Long userId, String doi, String activityType, Map<String, Object> metadata) {
        UserActivity activity = UserActivity.builder()
                .userId(userId)
                .doi(doi)
                .activityType(activityType)
                .metadata(metadata)
                .timestamp(LocalDateTime.now())
                .build();

        activityRepository.save(activity);
    }

    public List<UserActivityResponse> getRecentActivities(Long userId, int limit) {
        if (limit < 1) {
            limit = 10;
        }
        List<UserActivity> activities = activityRepository.findRecentViewsByUserId(
                userId,
                PageRequest.of(0, limit, Sort.by(Sort.Direction.DESC, "timestamp"))
        );

        return activities.stream()
                .map(UserActivityResponse::from)
                .toList();
    }
}
