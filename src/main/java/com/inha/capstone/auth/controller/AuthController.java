package com.inha.capstone.auth.controller;

import com.inha.capstone.auth.dto.LoginRequest;
import com.inha.capstone.auth.dto.LoginResponse;
import com.inha.capstone.auth.dto.RefreshRequest;
import com.inha.capstone.auth.jwt.JwtTokenProvider;
import com.inha.capstone.auth.security.JwtAuthenticationToken;
import com.inha.capstone.auth.service.AuthService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/auth")
@RequiredArgsConstructor
public class AuthController {

    private final AuthService authService;
    private final JwtTokenProvider jwtTokenProvider;

    @PostMapping("/login")
    public ResponseEntity<LoginResponse> login(@RequestBody @Valid LoginRequest request) {
        LoginResponse response = authService.login(request);
        return ResponseEntity.ok(response);
    }

    @PostMapping("/refresh")
    public ResponseEntity<LoginResponse> refresh(@RequestBody @Valid RefreshRequest request) {
        LoginResponse response = authService.refresh(request);
        return ResponseEntity.ok(response);
    }

    @PostMapping("/logout")
    public ResponseEntity<Void> logout(
            @AuthenticationPrincipal JwtAuthenticationToken authentication,
            @RequestHeader("Authorization") String authorizationHeader
    ) {
        String accessToken = jwtTokenProvider.extractBearerToken(authorizationHeader);
        authService.logout(authentication.getUserId(), accessToken);
        return ResponseEntity.status(HttpStatus.NO_CONTENT).build();
    }
}
