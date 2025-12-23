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

@Slf4j
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
        // Just fetching views as requested by repo query, but let's make it generic if Controller wants all
        // For now, mirroring findRecentViewsByUserId in logic, but let's assume we want a generic get for API
        // But ActivityRepository only has findRecentViewsByUserId (custom query).
        // Let's rely on that for now if the requirement is main "view" history. 
        // Or better, standard findByUserId with Sort.
        
        // Actually, let's implement a standard findByUserId manually or just use Repository
        // Since ActivityRepository extends specific MongoRepository, standard methods are available.
        // We'll use findAll with Example or Criteria if strictly needed, but let's keep it simple.
        
        // Let's use the custom method I added for recent views as that's the main user-facing history
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
