package com.inha.capstone.activity.controller;

import com.inha.capstone.activity.dto.UserActivityDto;
import com.inha.capstone.activity.service.ActivityService;
import com.inha.capstone.auth.security.UserPrincipal;
import com.inha.capstone.user.domain.User;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/activities")
@RequiredArgsConstructor
public class ActivityController {

    private final ActivityService activityService;

    @GetMapping("/recent")
    public ResponseEntity<List<UserActivityDto>> getRecentActivities(
            @AuthenticationPrincipal UserPrincipal userPrincipal,
            @RequestParam(defaultValue = "50") int limit
    ) {
        if (userPrincipal == null) {
            return ResponseEntity.status(401).build();
        }
        User user = userPrincipal.getUser();
        return ResponseEntity.ok(activityService.getRecentActivities(user, limit));
    }
}
