package com.inha.capstone.bookmark.model;

import lombok.AccessLevel;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;
import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.mapping.Document;
import org.springframework.data.mongodb.core.mapping.Field;

import java.time.LocalDateTime;

@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
@AllArgsConstructor(access = AccessLevel.PRIVATE)
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
