package com.inha.capstone.bookmark.dto;

import lombok.Builder;

// Request DTOs often use standard classes for validation frameworks, 
// but records are also supported for @RequestBody in newer Spring Boot.
// Using record for consistency as requested "ALL DTOs".
// Adding Builder just in case, though usually requests are deser'd by Jackson.
@Builder 
public record BookmarkCreateRequest(
    String doi,
    String notes
) {}
