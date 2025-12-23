package com.inha.capstone.activity.model;

import lombok.Builder;
import lombok.Data;
import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.mapping.Document;
import org.springframework.data.mongodb.core.mapping.Field;

import java.time.LocalDateTime;
import java.util.Map;

@Data
@Builder
@Document(collection = "user_activities")
public class UserActivity {
    @Id
    private String id;
    
    @Field("user_id")
    private Long userId;
    
    private String doi;
    
    @Field("activity_type")
    private String activityType;
    
    // activity_logger.py uses 'metadata' field which is a dict/map
    private Map<String, Object> metadata;
    
    private LocalDateTime timestamp;
}
