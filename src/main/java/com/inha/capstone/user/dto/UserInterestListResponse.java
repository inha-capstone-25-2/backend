package com.inha.capstone.user.dto;

import java.util.List;

public record UserInterestListResponse(
    List<String> categories
) {
    public static UserInterestListResponse of(List<String> categories) {
        return new UserInterestListResponse(categories);
    }
}
