package com.inha.capstone.paper.dto;

import lombok.Builder;

import java.util.List;

@Builder
public record PaperSearchResponse(
    int page,
    int pageSize,
    long total,
    int totalPages,
    boolean hasNext,
    boolean hasPrev,
    boolean isApproximate,
    List<PaperListItem> items
) {}
