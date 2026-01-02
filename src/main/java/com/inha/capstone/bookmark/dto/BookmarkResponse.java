package com.inha.capstone.bookmark.dto;

import com.inha.capstone.bookmark.model.Bookmark;
import com.inha.capstone.paper.model.Paper;

import java.time.LocalDateTime;

public record BookmarkResponse(
    String id,
    Long userId,
    String doi,
    LocalDateTime bookmarkedAt,
    String journalRef,
    String notes,
    String title,
    String authors
) {
    public static BookmarkResponse of(Bookmark bookmark, Paper paper) {
        return new BookmarkResponse(
            bookmark.getId(),
            bookmark.getUserId(),
            bookmark.getDoi(),
            bookmark.getBookmarkedAt(),
            paper != null ? paper.getJournalRef() : "Unknown",
            bookmark.getNotes(),
            paper != null ? paper.getTitle() : "Unknown",
            paper != null ? paper.getAuthors() : "Unknown"
        );
    }
}
