package com.inha.capstone.user.dto;

import lombok.AllArgsConstructor;
import lombok.Getter;
import lombok.NoArgsConstructor;

import java.util.List;

public class UserInterestDto {

    @Getter
    @NoArgsConstructor
    @AllArgsConstructor
    public static class InterestAddRequest {
        private List<String> categoryCodes;
    }

    @Getter
    @AllArgsConstructor
    public static class InterestListResponse {
        private List<String> categories;
    }

    @Getter
    @AllArgsConstructor
    public static class InterestRemovalResult {
        private int removedCount;
    }
}
