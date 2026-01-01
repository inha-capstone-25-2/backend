package com.inha.capstone.bookmark.model;

import lombok.Builder;
import lombok.Data;
import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.mapping.Document;
import org.springframework.data.mongodb.core.mapping.Field;

import java.time.LocalDateTime;

@Data
@Builder
@Document(collection = "bookmarks")
public class Bookmark {
    @Id
    private String id;
    
    @Field("user_id")
    private Long userId;
    
    private String doi;
    
    @Field("bookmarked_at")
    private LocalDateTime bookmarkedAt;
    
    private String notes;
}
