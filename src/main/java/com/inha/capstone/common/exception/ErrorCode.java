package com.inha.capstone.common.exception;

import lombok.Getter;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;

@Getter
@RequiredArgsConstructor
public enum ErrorCode {

    // User
    DUPLICATE_USERNAME(HttpStatus.CONFLICT, "U001", "이미 사용 중인 아이디입니다."),
    DUPLICATE_EMAIL(HttpStatus.CONFLICT, "U002", "이미 사용 중인 이메일입니다."),
    USER_NOT_FOUND(HttpStatus.NOT_FOUND, "U003", "User not found"),
    ALREADY_REGISTERED_USER(HttpStatus.CONFLICT, "U004", "이미 가입된 회원 정보가 존재합니다.");

    private final HttpStatus status;
    private final String code;
    private final String message;
}
