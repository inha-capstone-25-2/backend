package com.inha.capstone.auth.dto;

import com.inha.capstone.user.domain.User;

import java.time.LocalDateTime;

public record UserResponse(
    Long id,
    String email,
    String username,
    String name,
    LocalDateTime createdAt
) {
    public static UserResponse from(User user) {
        return new UserResponse(
            user.getId(),
            user.getEmail(),
            user.getUsername(),
            user.getName(),
            user.getCreatedAt()
        );
    }
}
