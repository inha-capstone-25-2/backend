package com.inha.capstone.user.controller;

import com.inha.capstone.auth.security.UserPrincipal;
import com.inha.capstone.user.domain.User;
import com.inha.capstone.user.dto.UserInterestDto;
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

    @PostMapping
    public ResponseEntity<List<String>> addInterests(
            @AuthenticationPrincipal UserPrincipal userPrincipal,
            @RequestBody UserInterestDto.InterestAddRequest request
    ) {
        if (userPrincipal == null) {
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED).build();
        }
        User user = userPrincipal.getUser();
        List<String> result = userInterestService.addInterests(user, request.getCategoryCodes());
        return ResponseEntity.status(HttpStatus.CREATED).body(result);
    }

    @GetMapping
    public ResponseEntity<UserInterestDto.InterestListResponse> listInterests(
            @AuthenticationPrincipal UserPrincipal userPrincipal
    ) {
        if (userPrincipal == null) {
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED).build();
        }
        User user = userPrincipal.getUser();
        return ResponseEntity.ok(userInterestService.listInterests(user));
    }

    @DeleteMapping
    public ResponseEntity<UserInterestDto.InterestRemovalResult> removeInterests(
            @AuthenticationPrincipal UserPrincipal userPrincipal,
            @RequestParam(name = "codes") List<String> codes
    ) {
        if (userPrincipal == null) {
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED).build();
        }
        User user = userPrincipal.getUser();
        return ResponseEntity.ok(userInterestService.removeInterests(user, codes));
    }
}
