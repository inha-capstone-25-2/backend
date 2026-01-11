package com.inha.capstone.user.controller;

import com.inha.capstone.auth.dto.UserResponse;
import com.inha.capstone.auth.dto.UsernameExistsResponse;
import com.inha.capstone.auth.security.JwtAuthenticationToken;
import com.inha.capstone.auth.service.AuthService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/users")
@RequiredArgsConstructor
public class UserController {

    private final AuthService authService;

    @GetMapping("/me")
    public ResponseEntity<UserResponse> me(@AuthenticationPrincipal JwtAuthenticationToken authentication) {
        return ResponseEntity.ok(authService.getUserById(authentication.getUserId()));
    }

    @DeleteMapping("/me")
    public ResponseEntity<Void> quit(@AuthenticationPrincipal JwtAuthenticationToken authentication) {
        authService.deleteAccount(authentication.getUserId());
        return ResponseEntity.status(HttpStatus.NO_CONTENT).build();
    }

    @GetMapping("/exists")
    public ResponseEntity<UsernameExistsResponse> checkUsernameExists(@RequestParam String username) {
        boolean exists = authService.checkUsernameExists(username);
        return ResponseEntity.ok(new UsernameExistsResponse(exists));
    }
}
