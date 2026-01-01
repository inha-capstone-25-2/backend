package com.inha.capstone.user.dto;

public record UserInterestRemovalResponse(
    int removedCount
) {
    public static UserInterestRemovalResponse of(int removedCount) {
        return new UserInterestRemovalResponse(removedCount);
    }
}
