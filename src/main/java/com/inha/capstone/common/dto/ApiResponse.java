package com.inha.capstone.common.dto;

import com.fasterxml.jackson.annotation.JsonInclude;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;

@JsonInclude(JsonInclude.Include.NON_NULL)
public record ApiResponse<T>(
        boolean success,
        T data,
        String error,
        String message,
        String timestamp
) {

    private static final DateTimeFormatter ISO_FORMATTER = DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ss");

    public static <T> ApiResponse<T> of(T data) {
        return new ApiResponse<>(
                true,
                data,
                null,
                null,
                LocalDateTime.now().format(ISO_FORMATTER)
        );
    }

    public static ApiResponse<Void> empty() {
        return new ApiResponse<>(
                true,
                null,
                null,
                null,
                LocalDateTime.now().format(ISO_FORMATTER)
        );
    }

    public static ApiResponse<Void> error(String error, String message) {
        return new ApiResponse<>(
                false,
                null,
                error,
                message,
                LocalDateTime.now().format(ISO_FORMATTER)
        );
    }
}
