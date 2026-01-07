package com.inha.capstone.auth.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

public record LoginResponse(
    @JsonProperty("access_token") String accessToken,
    @JsonProperty("refresh_token") String refreshToken,
    @JsonProperty("token_type") String tokenType,
    @JsonProperty("expires_in") long expiresIn
) {
    public static LoginResponse of(String accessToken, String refreshToken, long expiresInSeconds) {
        return new LoginResponse(accessToken, refreshToken, "Bearer", expiresInSeconds);
    }
}
