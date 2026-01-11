package com.inha.capstone.activity.controller;

import com.inha.capstone.activity.dto.UserActivityResponse;
import com.inha.capstone.activity.service.ActivityService;
import com.inha.capstone.auth.security.JwtAuthenticationToken;
import com.inha.capstone.common.exception.CustomException;
import com.inha.capstone.common.exception.ErrorCode;
import com.inha.capstone.user.domain.User;
import com.inha.capstone.user.repository.UserRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/api/activities")
@RequiredArgsConstructor
public class ActivityController {

    private final ActivityService activityService;
    private final UserRepository userRepository;

    @GetMapping("/recent")
    public ResponseEntity<List<UserActivityResponse>> getRecentActivities(
            @AuthenticationPrincipal JwtAuthenticationToken authentication,
            @RequestParam(defaultValue = "50") int limit
    ) {
        User user = findUserById(authentication.getUserId());
        return ResponseEntity.ok(activityService.getRecentActivities(user, limit));
    }

    private User findUserById(Long userId) {
        return userRepository.findById(userId)
                .orElseThrow(() -> new CustomException(ErrorCode.USER_NOT_FOUND));
    }
}
