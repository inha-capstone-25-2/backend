package com.inha.capstone.paper.dto;

import com.inha.capstone.paper.model.Paper;
import lombok.Builder;

import java.time.LocalDateTime;
import java.util.List;

@Builder
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
        return PaperListItem.builder()
                .id(paper.getId())
                .title(paper.getTitle())
                .authors(paper.getAuthors())
                .categories(paper.getCategories())
                .updateDate(paper.getUpdateDate())
                .viewCount(paper.getViewCount())
                .journalRef(paper.getJournalRef())
                .build();
    }
}
