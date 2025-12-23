package com.inha.capstone.bookmark.service;

import com.inha.capstone.bookmark.dto.BookmarkCreateRequest;
import com.inha.capstone.bookmark.dto.BookmarkDto;
import com.inha.capstone.bookmark.model.Bookmark;
import com.inha.capstone.bookmark.repository.BookmarkRepository;
import com.inha.capstone.paper.model.Paper;
import com.inha.capstone.paper.repository.PaperRepository;
import com.inha.capstone.user.domain.User;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.test.util.ReflectionTestUtils;

import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.BDDMockito.given;
import static org.mockito.BDDMockito.then;

@ExtendWith(MockitoExtension.class)
class BookmarkServiceTest {

    @Mock
    private BookmarkRepository bookmarkRepository;

    @Mock
    private PaperRepository paperRepository;

    @InjectMocks
    private BookmarkService bookmarkService;

    @Nested
    class CreateBookmark {

        @Test
        void 북마크_생성_성공() {
            // given
            User user = User.builder().build();
            ReflectionTestUtils.setField(user, "id", 1L);
            BookmarkCreateRequest request = BookmarkCreateRequest.builder()
                    .doi("10.1234/5678")
                    .build();
            
            given(paperRepository.findById("10.1234/5678")).willReturn(Optional.of(new Paper()));
            given(bookmarkRepository.findByUserIdAndDoi(1L, "10.1234/5678")).willReturn(Optional.empty());
            given(bookmarkRepository.save(any(Bookmark.class))).willAnswer(i -> i.getArguments()[0]);

            // when
            BookmarkDto result = bookmarkService.createBookmark(user, request);

            // then
            assertThat(result).isNotNull();
            
            then(paperRepository).should().findById("10.1234/5678");
            then(bookmarkRepository).should().save(any(Bookmark.class));
        }
    }
}
