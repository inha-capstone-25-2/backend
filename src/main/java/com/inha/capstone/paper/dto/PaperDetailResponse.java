package com.inha.capstone.paper.dto;

import com.inha.capstone.paper.model.Paper;

import java.util.List;

public record PaperDetailResponse(
    String id,
    String title,
    SummaryDto summary,
    String authors,
    List<String> categories,
    String updateDate,
    Integer viewCount,
    String journalRef,
    String reportNo,
    String doi,
    String license,
    List<VersionDto> versions,
    List<List<String>> authorsParsed
) {
    public static PaperDetailResponse from(Paper paper) {
        return new PaperDetailResponse(
            paper.getId(),
            paper.getTitle(),
            paper.getSummary() != null ? SummaryDto.from(paper.getSummary()) : null,
            paper.getAuthors(),
            paper.getCategories(),
            paper.getUpdateDate(),
            paper.getViewCount(),
            paper.getJournalRef(),
            paper.getReportNo(),
            paper.getDoi(),
            paper.getLicense(),
            paper.getVersions() != null ? paper.getVersions().stream()
                .map(VersionDto::from)
                .toList() : null,
            paper.getAuthorsParsed()
        );
    }

    public record SummaryDto(
        String en,
        String ko
    ) {
        public static SummaryDto from(Paper.Summary summary) {
            return new SummaryDto(
                summary.getEn(),
                summary.getKo()
            );
        }
    }

    public record VersionDto(
        String version,
        String created
    ) {
        public static VersionDto from(Paper.Version version) {
            return new VersionDto(
                version.getVersion(),
                version.getCreated()
            );
        }
    }
}
