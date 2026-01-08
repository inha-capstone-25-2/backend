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
    USER_NOT_FOUND(HttpStatus.NOT_FOUND, "U003", "사용자를 찾을 수 없습니다."),
    ALREADY_REGISTERED_USER(HttpStatus.CONFLICT, "U004", "이미 가입된 회원 정보가 존재합니다."),

    // Paper
    PAPER_NOT_FOUND(HttpStatus.NOT_FOUND, "P001", "논문을 찾을 수 없습니다."),

    // Bookmark
    BOOKMARK_ALREADY_EXISTS(HttpStatus.CONFLICT, "B001", "이미 북마크에 추가된 논문입니다."),
    BOOKMARK_NOT_FOUND(HttpStatus.NOT_FOUND, "B002", "북마크를 찾을 수 없습니다."),

    // Authorization
    UNAUTHENTICATED(HttpStatus.UNAUTHORIZED, "A001", "로그인이 필요합니다."),
    FORBIDDEN(HttpStatus.FORBIDDEN, "A002", "접근 권한이 없습니다."),
    INVALID_CREDENTIALS(HttpStatus.UNAUTHORIZED, "A003", "잘못된 아이디 또는 비밀번호입니다."),
    INVALID_TOKEN(HttpStatus.UNAUTHORIZED, "A004", "유효하지 않은 토큰입니다."),
    EXPIRED_TOKEN(HttpStatus.UNAUTHORIZED, "A005", "만료된 토큰입니다.");

    private final HttpStatus status;
    private final String code;
    private final String message;
}
