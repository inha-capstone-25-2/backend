package com.inha.capstone.bookmark.service;

import com.inha.capstone.bookmark.dto.BookmarkCreateRequest;
import com.inha.capstone.bookmark.dto.BookmarkResponse;
import com.inha.capstone.bookmark.model.Bookmark;
import com.inha.capstone.bookmark.repository.BookmarkRepository;
import com.inha.capstone.common.exception.CustomException;
import com.inha.capstone.common.exception.ErrorCode;
import com.inha.capstone.paper.model.Paper;
import com.inha.capstone.paper.repository.PaperRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.List;

@Service
@RequiredArgsConstructor
public class BookmarkService {

    private final BookmarkRepository bookmarkRepository;
    private final PaperRepository paperRepository;

    public BookmarkResponse createBookmark(Long userId, BookmarkCreateRequest request) {
        Paper paper = paperRepository.findById(request.doi())
                .orElseThrow(() -> new CustomException(ErrorCode.PAPER_NOT_FOUND));

        if (bookmarkRepository.findByUserIdAndDoi(userId, request.doi()).isPresent()) {
            throw new CustomException(ErrorCode.BOOKMARK_ALREADY_EXISTS);
        }

        Bookmark bookmark = Bookmark.builder()
                .userId(userId)
                .doi(request.doi())
                .notes(request.notes())
                .bookmarkedAt(LocalDateTime.now())
                .build();

        Bookmark saved = bookmarkRepository.save(bookmark);

        return BookmarkResponse.of(saved, paper);
    }

    public List<BookmarkResponse> getBookmarks(Long userId) {
        List<Bookmark> bookmarks = bookmarkRepository.findByUserIdOrderByBookmarkedAtDesc(userId);

        return bookmarks.stream()
                .map(bookmark -> {
                    Paper paper = paperRepository.findById(bookmark.getDoi()).orElse(null);
                    return BookmarkResponse.of(bookmark, paper);
                })
                .toList();
    }

    public void deleteBookmark(Long userId, String bookmarkId) {
        Bookmark bookmark = bookmarkRepository.findById(bookmarkId)
                .orElseThrow(() -> new CustomException(ErrorCode.BOOKMARK_NOT_FOUND));

        if (!bookmark.getUserId().equals(userId)) {
            throw new CustomException(ErrorCode.FORBIDDEN);
        }

        bookmarkRepository.delete(bookmark);
    }
}
