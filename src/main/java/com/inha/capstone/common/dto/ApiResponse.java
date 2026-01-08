package com.inha.capstone.common.dto;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.inha.capstone.common.exception.ErrorCode;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;

@JsonInclude(JsonInclude.Include.NON_NULL)
public record ApiResponse<T>(
        boolean success,
        T data,
        ErrorResponse error,
        String timestamp
) {

    private static final DateTimeFormatter ISO_FORMATTER = DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ss");

    public static <T> ApiResponse<T> of(T data) {
        return new ApiResponse<>(
                true,
                data,
                null,
                LocalDateTime.now().format(ISO_FORMATTER)
        );
    }

    public static ApiResponse<Void> empty() {
        return new ApiResponse<>(
                true,
                null,
                null,
                LocalDateTime.now().format(ISO_FORMATTER)
        );
    }

    public static ApiResponse<Void> error(ErrorResponse error) {
        return new ApiResponse<>(
                false,
                null,
                error,
                LocalDateTime.now().format(ISO_FORMATTER)
        );
    }

    public static ApiResponse<Void> error(ErrorCode errorCode) {
        return new ApiResponse<>(
                false,
                null,
                ErrorResponse.of(errorCode),
                LocalDateTime.now().format(ISO_FORMATTER)
        );
    }
}
