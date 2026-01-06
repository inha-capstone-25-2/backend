package com.inha.capstone.common.exception;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;

public record ErrorResponse(
        String error,
        String message,
        String code,
        String timestamp
) {

    private static final DateTimeFormatter ISO_FORMATTER = DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ss");

    public static ErrorResponse from(ErrorCode errorCode) {
        return new ErrorResponse(
                errorCode.getStatus().getReasonPhrase(),
                errorCode.getMessage(),
                errorCode.getCode(),
                LocalDateTime.now().format(ISO_FORMATTER)
        );
    }

    public static ErrorResponse of(String error, String message) {
        return new ErrorResponse(
                error,
                message,
                null,
                LocalDateTime.now().format(ISO_FORMATTER)
        );
    }
}
