package com.inha.capstone.paper.dto;

import com.inha.capstone.paper.model.Paper;

import java.util.List;

public record PaperListItem(
    String id,
    String title,
    String authors,
    List<String> categories,
    String updateDate,
    Integer viewCount,
    String journalRef
) {
    public static PaperListItem from(Paper paper) {
        return new PaperListItem(
            paper.getId(),
            paper.getTitle(),
            paper.getAuthors(),
            paper.getCategories(),
            paper.getUpdateDate(),
            paper.getViewCount(),
            paper.getJournalRef()
        );
    }
}
