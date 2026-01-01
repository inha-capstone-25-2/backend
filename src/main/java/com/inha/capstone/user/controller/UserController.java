package com.inha.capstone.user.controller;

import com.inha.capstone.auth.dto.UserCreateRequest;
import com.inha.capstone.auth.dto.UserResponse;
import com.inha.capstone.auth.dto.UsernameExistsResponse;
import com.inha.capstone.auth.security.UserPrincipal;
import com.inha.capstone.auth.service.AuthService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/users")
@RequiredArgsConstructor
public class UserController {

    private final AuthService authService;

    @PostMapping
    public ResponseEntity<UserResponse> register(@RequestBody @Valid UserCreateRequest request) {
        UserResponse response = authService.register(request);
        return ResponseEntity.status(HttpStatus.CREATED).body(response);
    }

    @GetMapping("/me")
    public ResponseEntity<UserResponse> me(@AuthenticationPrincipal UserPrincipal userPrincipal) {
        return ResponseEntity.ok(UserResponse.from(userPrincipal.getUser()));
    }

    @DeleteMapping("/me")
    public ResponseEntity<Void> quit(@AuthenticationPrincipal UserPrincipal userPrincipal) {
        authService.deleteAccount(userPrincipal.getUser().getId());
        return ResponseEntity.status(HttpStatus.NO_CONTENT).build();
    }

    @GetMapping("/exists")
    public ResponseEntity<UsernameExistsResponse> checkUsernameExists(@RequestParam String username) {
        boolean exists = authService.checkUsernameExists(username);
        return ResponseEntity.ok(new UsernameExistsResponse(exists));
    }
}
