package com.inha.capstone.user.controller;

import com.inha.capstone.auth.security.JwtAuthenticationToken;
import com.inha.capstone.common.exception.CustomException;
import com.inha.capstone.common.exception.ErrorCode;
import com.inha.capstone.user.domain.User;
import com.inha.capstone.user.dto.UserInterestAddRequest;
import com.inha.capstone.user.dto.UserInterestListResponse;
import com.inha.capstone.user.dto.UserInterestRemovalResponse;
import com.inha.capstone.user.repository.UserRepository;
import com.inha.capstone.user.service.UserInterestService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/api/user-interests")
@RequiredArgsConstructor
public class UserInterestController {

    private final UserInterestService userInterestService;
    private final UserRepository userRepository;

    @PostMapping
    public ResponseEntity<List<String>> addInterests(
            @AuthenticationPrincipal JwtAuthenticationToken authentication,
            @RequestBody UserInterestAddRequest request
    ) {
        User user = findUserById(authentication.getUserId());
        List<String> result = userInterestService.addInterests(user, request.categoryCodes());
        return ResponseEntity.status(HttpStatus.CREATED).body(result);
    }

    @GetMapping
    public ResponseEntity<UserInterestListResponse> listInterests(
            @AuthenticationPrincipal JwtAuthenticationToken authentication
    ) {
        User user = findUserById(authentication.getUserId());
        return ResponseEntity.ok(userInterestService.listInterests(user));
    }

    @DeleteMapping
    public ResponseEntity<UserInterestRemovalResponse> removeInterests(
            @AuthenticationPrincipal JwtAuthenticationToken authentication,
            @RequestParam(name = "codes") List<String> codes
    ) {
        User user = findUserById(authentication.getUserId());
        return ResponseEntity.ok(userInterestService.removeInterests(user, codes));
    }

    private User findUserById(Long userId) {
        return userRepository.findById(userId)
                .orElseThrow(() -> new CustomException(ErrorCode.USER_NOT_FOUND));
    }
}
