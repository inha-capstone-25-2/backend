package com.inha.capstone.bookmark.dto;

import lombok.Builder;

@Builder 
public record BookmarkCreateRequest(
    String doi,
    String notes
) {}
