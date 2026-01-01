package com.inha.capstone.auth.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

public record TokenResponse(
    @JsonProperty("access_token") String accessToken,
    @JsonProperty("token_type") String tokenType
) {
    public TokenResponse(String accessToken) {
        this(accessToken, "bearer");
    }
}
