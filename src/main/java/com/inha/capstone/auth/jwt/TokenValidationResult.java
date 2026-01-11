package com.inha.capstone.auth.jwt;

public enum TokenValidationResult {

    VALID,
    EXPIRED,
    INVALID_SIGNATURE,
    MALFORMED,
    UNSUPPORTED
}
