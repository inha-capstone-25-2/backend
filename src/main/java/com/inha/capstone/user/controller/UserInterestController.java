package com.inha.capstone.user.controller;

import com.inha.capstone.auth.security.UserPrincipal;
import com.inha.capstone.user.dto.UserInterestAddRequest;
import com.inha.capstone.user.dto.UserInterestListResponse;
import com.inha.capstone.user.dto.UserInterestRemovalResponse;
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
            @RequestBody UserInterestAddRequest request
    ) {
        List<String> result = userInterestService.addInterests(userPrincipal.getUser(), request.categoryCodes());
        return ResponseEntity.status(HttpStatus.CREATED).body(result);
    }

    @GetMapping
    public ResponseEntity<UserInterestListResponse> listInterests(
            @AuthenticationPrincipal UserPrincipal userPrincipal
    ) {
        return ResponseEntity.ok(userInterestService.listInterests(userPrincipal.getUser()));
    }

    @DeleteMapping
    public ResponseEntity<UserInterestRemovalResponse> removeInterests(
            @AuthenticationPrincipal UserPrincipal userPrincipal,
            @RequestParam(name = "codes") List<String> codes
    ) {
        return ResponseEntity.ok(userInterestService.removeInterests(userPrincipal.getUser(), codes));
    }
}

