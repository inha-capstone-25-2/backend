package com.inha.capstone.activity.model;

import lombok.AccessLevel;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;
import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.mapping.Document;
import org.springframework.data.mongodb.core.mapping.Field;

import java.time.LocalDateTime;
import java.util.Map;

@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
@AllArgsConstructor(access = AccessLevel.PRIVATE)
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
    
    private Map<String, Object> metadata;
    
    private LocalDateTime timestamp;
}
