package com.inha.capstone.activity.controller;

import com.inha.capstone.activity.dto.UserActivityResponse;
import com.inha.capstone.activity.service.ActivityService;
import com.inha.capstone.auth.security.UserPrincipal;
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

    @GetMapping("/recent")
    public ResponseEntity<List<UserActivityResponse>> getRecentActivities(
            @AuthenticationPrincipal UserPrincipal userPrincipal,
            @RequestParam(defaultValue = "50") int limit
    ) {
        return ResponseEntity.ok(activityService.getRecentActivities(userPrincipal.getUser(), limit));
    }
}

