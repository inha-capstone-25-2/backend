package com.inha.capstone.common.exception;

import lombok.Getter;

@Getter
public class DuplicateUserException extends BusinessException {

    public DuplicateUserException(ErrorCode errorCode) {
        super(errorCode);
    }
}
