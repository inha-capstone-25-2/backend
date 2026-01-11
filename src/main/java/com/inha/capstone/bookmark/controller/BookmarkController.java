package com.inha.capstone.bookmark.controller;

import com.inha.capstone.auth.security.JwtAuthenticationToken;
import com.inha.capstone.bookmark.dto.BookmarkCreateRequest;
import com.inha.capstone.bookmark.dto.BookmarkResponse;
import com.inha.capstone.bookmark.service.BookmarkService;
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

    @PostMapping
    public ResponseEntity<BookmarkResponse> createBookmark(
            @AuthenticationPrincipal JwtAuthenticationToken authentication,
            @RequestBody BookmarkCreateRequest request
    ) {
        return ResponseEntity.ok(bookmarkService.createBookmark(authentication.getUserId(), request));
    }

    @GetMapping
    public ResponseEntity<List<BookmarkResponse>> getBookmarks(
            @AuthenticationPrincipal JwtAuthenticationToken authentication
    ) {
        return ResponseEntity.ok(bookmarkService.getBookmarks(authentication.getUserId()));
    }

    @DeleteMapping("/{bookmarkId}")
    public ResponseEntity<Void> deleteBookmark(
            @AuthenticationPrincipal JwtAuthenticationToken authentication,
            @PathVariable String bookmarkId
    ) {
        bookmarkService.deleteBookmark(authentication.getUserId(), bookmarkId);
        return ResponseEntity.ok().build();
    }
}
