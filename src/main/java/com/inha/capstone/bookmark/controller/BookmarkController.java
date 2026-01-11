package com.inha.capstone.bookmark.controller;

import com.inha.capstone.auth.security.JwtAuthenticationToken;
import com.inha.capstone.bookmark.dto.BookmarkCreateRequest;
import com.inha.capstone.bookmark.dto.BookmarkResponse;
import com.inha.capstone.bookmark.service.BookmarkService;
import com.inha.capstone.common.exception.CustomException;
import com.inha.capstone.common.exception.ErrorCode;
import com.inha.capstone.user.domain.User;
import com.inha.capstone.user.repository.UserRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/api/bookmarks")
@RequiredArgsConstructor
public class BookmarkController {

    private final BookmarkService bookmarkService;
    private final UserRepository userRepository;

    @PostMapping
    public ResponseEntity<BookmarkResponse> createBookmark(
            @AuthenticationPrincipal JwtAuthenticationToken authentication,
            @RequestBody BookmarkCreateRequest request
    ) {
        User user = findUserById(authentication.getUserId());
        return ResponseEntity.ok(bookmarkService.createBookmark(user, request));
    }

    @GetMapping
    public ResponseEntity<List<BookmarkResponse>> getBookmarks(
            @AuthenticationPrincipal JwtAuthenticationToken authentication
    ) {
        User user = findUserById(authentication.getUserId());
        return ResponseEntity.ok(bookmarkService.getBookmarks(user));
    }

    @DeleteMapping("/{bookmarkId}")
    public ResponseEntity<Void> deleteBookmark(
            @AuthenticationPrincipal JwtAuthenticationToken authentication,
            @PathVariable String bookmarkId
    ) {
        User user = findUserById(authentication.getUserId());
        bookmarkService.deleteBookmark(user, bookmarkId);
        return ResponseEntity.ok().build();
    }

    private User findUserById(Long userId) {
        return userRepository.findById(userId)
                .orElseThrow(() -> new CustomException(ErrorCode.USER_NOT_FOUND));
    }
}
