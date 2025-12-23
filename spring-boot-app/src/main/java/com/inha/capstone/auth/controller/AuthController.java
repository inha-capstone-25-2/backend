package com.inha.capstone.auth.controller;

import com.inha.capstone.auth.dto.*;
import com.inha.capstone.auth.security.UserPrincipal;
import com.inha.capstone.auth.service.AuthService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/auth")
@RequiredArgsConstructor
public class AuthController {

    private final AuthService authService;

    @PostMapping("/register")
    public ResponseEntity<UserResponse> register(@RequestBody @Valid UserCreateRequest request) {
        UserResponse response = authService.register(request);
        return ResponseEntity.status(HttpStatus.CREATED).body(response);
    }

    @PostMapping("/login")
    public ResponseEntity<TokenResponse> login(@RequestBody @Valid LoginRequest request) {
        TokenResponse response = authService.login(request);
        return ResponseEntity.ok(response);
    }

    @GetMapping("/username-exists")
    public ResponseEntity<UsernameExistsResponse> checkUsernameExists(@RequestParam String username) {
        boolean exists = authService.checkUsernameExists(username);
        return ResponseEntity.ok(new UsernameExistsResponse(exists));
    }

    @GetMapping("/me")
    public ResponseEntity<UserResponse> me(@AuthenticationPrincipal UserPrincipal userPrincipal) {
        return ResponseEntity.ok(UserResponse.from(userPrincipal.getUser()));
    }

    @PostMapping("/logout")
    public ResponseEntity<Void> logout(@AuthenticationPrincipal UserPrincipal userPrincipal) {
        authService.logout(userPrincipal.getUser().getId());
        return ResponseEntity.status(HttpStatus.NO_CONTENT).build();
    }

    @DeleteMapping("/quit")
    public ResponseEntity<Void> quit(@AuthenticationPrincipal UserPrincipal userPrincipal) {
        authService.deleteAccount(userPrincipal.getUser().getId());
        return ResponseEntity.status(HttpStatus.NO_CONTENT).build();
    }
}
