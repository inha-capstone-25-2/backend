package com.inha.capstone.activity.service;

import com.inha.capstone.activity.dto.UserActivityDto;
import com.inha.capstone.activity.model.UserActivity;
import com.inha.capstone.activity.repository.ActivityRepository;
import com.inha.capstone.user.domain.User;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Sort;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
public class ActivityService {
    private final ActivityRepository activityRepository;

    public void logActivity(User user, String doi, String activityType, Map<String, Object> metadata) {
        UserActivity activity = UserActivity.builder()
                .userId(user.getId())
                .doi(doi)
                .activityType(activityType)
                .metadata(metadata)
                .timestamp(LocalDateTime.now())
                .build();
        
        activityRepository.save(activity);
    }
    
    public List<UserActivityDto> getRecentActivities(User user, int limit) {
        if (limit < 1) {
            limit = 10;
        }
        List<UserActivity> activities = activityRepository.findRecentViewsByUserId(
                user.getId(), 
                PageRequest.of(0, limit, Sort.by(Sort.Direction.DESC, "timestamp"))
        );
        
        return activities.stream().map(a -> UserActivityDto.builder()
                .id(a.getId())
                .userId(a.getUserId())
                .doi(a.getDoi())
                .activityType(a.getActivityType())
                .metadata(a.getMetadata())
                .timestamp(a.getTimestamp())
                .build()).collect(Collectors.toList());
    }
}
