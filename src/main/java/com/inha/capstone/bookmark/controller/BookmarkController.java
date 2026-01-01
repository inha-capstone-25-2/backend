package com.inha.capstone.bookmark.controller;

import com.inha.capstone.auth.security.UserPrincipal;
import com.inha.capstone.bookmark.dto.BookmarkCreateRequest;
import com.inha.capstone.bookmark.dto.BookmarkResponse;
import com.inha.capstone.bookmark.service.BookmarkService;
import com.inha.capstone.user.domain.User;
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
            @AuthenticationPrincipal UserPrincipal userPrincipal,
            @RequestBody BookmarkCreateRequest request
    ) {
        if (userPrincipal == null) {
            return ResponseEntity.status(401).build();
        }
        User user = userPrincipal.getUser();
        return ResponseEntity.ok(bookmarkService.createBookmark(user, request));
    }

    @GetMapping
    public ResponseEntity<List<BookmarkResponse>> getBookmarks(
            @AuthenticationPrincipal UserPrincipal userPrincipal
    ) {
        if (userPrincipal == null) {
            return ResponseEntity.status(401).build();
        }
        User user = userPrincipal.getUser();
        return ResponseEntity.ok(bookmarkService.getBookmarks(user));
    }
    
    @DeleteMapping("/{bookmarkId}")
    public ResponseEntity<Void> deleteBookmark(
            @AuthenticationPrincipal UserPrincipal userPrincipal,
            @PathVariable String bookmarkId
    ) {
        if (userPrincipal == null) {
            return ResponseEntity.status(401).build();
        }
        User user = userPrincipal.getUser();
        bookmarkService.deleteBookmark(user, bookmarkId);
        return ResponseEntity.ok().build();
    }
}
