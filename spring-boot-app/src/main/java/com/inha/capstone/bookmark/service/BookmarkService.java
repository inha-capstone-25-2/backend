package com.inha.capstone.bookmark.service;

import com.inha.capstone.bookmark.dto.BookmarkCreateRequest;
import com.inha.capstone.bookmark.dto.BookmarkDto;
import com.inha.capstone.bookmark.model.Bookmark;
import com.inha.capstone.bookmark.repository.BookmarkRepository;
import com.inha.capstone.paper.model.Paper;
import com.inha.capstone.paper.repository.PaperRepository;
import com.inha.capstone.user.domain.User;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;
import java.util.stream.Collectors;

@Slf4j
@Service
@RequiredArgsConstructor
public class BookmarkService {
    private final BookmarkRepository bookmarkRepository;
    private final PaperRepository paperRepository;

    @Transactional
    public BookmarkDto createBookmark(User user, BookmarkCreateRequest request) {
        // Check if paper exists
        Paper paper = paperRepository.findById(request.getDoi())
                .orElseThrow(() -> new RuntimeException("Paper not found"));

        // Check if already bookmarked
        if (bookmarkRepository.findByUserIdAndDoi(user.getId(), request.getDoi()).isPresent()) {
            throw new RuntimeException("Already bookmarked");
        }

        Bookmark bookmark = Bookmark.builder()
                .userId(user.getId())
                .doi(request.getDoi())
                .notes(request.getNotes())
                .bookmarkedAt(LocalDateTime.now())
                .build();
        
        Bookmark saved = bookmarkRepository.save(bookmark);
        
        // Log activity (bookmark) - TODO
        
        return convertToDto(saved, paper);
    }
    
    @Transactional(readOnly = true)
    public List<BookmarkDto> getBookmarks(User user) {
        List<Bookmark> bookmarks = bookmarkRepository.findByUserIdOrderByBookmarkedAtDesc(user.getId());
        
        return bookmarks.stream().map(bookmark -> {
            Paper paper = paperRepository.findById(bookmark.getDoi()).orElse(null);
            return convertToDto(bookmark, paper);
        }).collect(Collectors.toList());
    }
    
    @Transactional
    public void deleteBookmark(User user, String bookmarkId) {
        Bookmark bookmark = bookmarkRepository.findById(bookmarkId)
                .orElseThrow(() -> new RuntimeException("Bookmark not found"));
        
        if (!bookmark.getUserId().equals(user.getId())) {
            throw new RuntimeException("Not authorized");
        }
        
        bookmarkRepository.delete(bookmark);
        // Log activity (unbookmark) - TODO
    }

    private BookmarkDto convertToDto(Bookmark bookmark, Paper paper) {
        return BookmarkDto.builder()
                .id(bookmark.getId())
                .userId(bookmark.getUserId())
                .doi(bookmark.getDoi())
                .bookmarkedAt(bookmark.getBookmarkedAt())
                .notes(bookmark.getNotes())
                .title(paper != null ? paper.getTitle() : "Unknown Paper")
                .authors(paper != null ? paper.getAuthors() : null)
                .journalRef(paper != null ? paper.getJournalRef() : null)
                .build();
    }
}
