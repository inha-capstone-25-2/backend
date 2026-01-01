package com.inha.capstone.bookmark.dto;

import lombok.Builder;
import java.time.LocalDateTime;

@Builder
public record BookmarkDto(
    String id,
    Long userId,
    String doi,
    LocalDateTime bookmarkedAt,
    String journalRef,
    String notes,
    String title, 
    String authors
) {}
