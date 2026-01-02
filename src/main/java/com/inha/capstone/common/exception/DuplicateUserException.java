package com.inha.capstone.common.exception;

import lombok.Getter;

@Getter
public class DuplicateUserException extends CustomException {

    public DuplicateUserException(ErrorCode errorCode) {
        super(errorCode);
    }
}
