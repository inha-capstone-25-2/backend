package com.inha.capstone.common.dto;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.inha.capstone.common.exception.ErrorCode;

import java.util.List;

@JsonInclude(JsonInclude.Include.NON_NULL)
public record ErrorResponse(
        String code,
        String message,
        int status,
        List<FieldError> errors
) {

    public record FieldError(String field, String message) {}

    public static ErrorResponse of(ErrorCode errorCode) {
        return new ErrorResponse(
                errorCode.getCode(),
                errorCode.getMessage(),
                errorCode.getStatus().value(),
                null
        );
    }

    public static ErrorResponse of(String code, String message, int status) {
        return new ErrorResponse(code, message, status, null);
    }
}
