package com.inha.capstone.bookmark.service;

import com.inha.capstone.bookmark.dto.BookmarkCreateRequest;
import com.inha.capstone.bookmark.dto.BookmarkDto;
import com.inha.capstone.bookmark.model.Bookmark;
import com.inha.capstone.bookmark.repository.BookmarkRepository;
import com.inha.capstone.paper.model.Paper;
import com.inha.capstone.paper.repository.PaperRepository;
import com.inha.capstone.user.domain.User;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.util.Optional;

import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class BookmarkServiceTest {

    @Mock
    private BookmarkRepository bookmarkRepository;

    @Mock
    private PaperRepository paperRepository;

    @InjectMocks
    private BookmarkService bookmarkService;

    @Test
    void createBookmark_shouldCreate_whenPaperExists() {
        // Given
        User user = User.builder().build();
        user.setId(1L);
        BookmarkCreateRequest request = BookmarkCreateRequest.builder()
                .doi("1234.5678")
                .build();
        
        when(paperRepository.findById("1234.5678")).thenReturn(Optional.of(new Paper()));
        when(bookmarkRepository.findByUserIdAndDoi(1L, "1234.5678")).thenReturn(Optional.empty());
        when(bookmarkRepository.save(any(Bookmark.class))).thenAnswer(i -> i.getArguments()[0]);

        // When
        BookmarkDto result = bookmarkService.createBookmark(user, request);

        // Then
        assertNotNull(result);
    }
}
