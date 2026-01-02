package com.inha.capstone.paper.service;

import com.inha.capstone.paper.dto.PaperDetailResponse;
import com.inha.capstone.paper.dto.PaperSearchResponse;
import com.inha.capstone.paper.model.Paper;
import com.inha.capstone.paper.repository.PaperRepository;
import com.inha.capstone.user.domain.User;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.data.mongodb.core.MongoTemplate;
import org.springframework.data.mongodb.core.query.Query;
import com.inha.capstone.paper.dto.PaperListItem; // Add import for check

import java.util.Collections;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.BDDMockito.given;

@ExtendWith(MockitoExtension.class)
class PaperServiceTest {

    @Mock
    private PaperRepository paperRepository;

    @Mock
    private MongoTemplate mongoTemplate;

    @InjectMocks
    private PaperService paperService;

    @Nested
    class SearchPapers {

        @Test
        void 키워드_검색_성공() {
            // given
            User user = User.builder().build();
            String query = "AI";

            Paper paper = Paper.builder()
                    .id("1")
                    .title("Introduction to AI")
                    .build();

            given(mongoTemplate.count(any(Query.class), eq(Paper.class))).willReturn(1L);
            given(mongoTemplate.find(any(Query.class), eq(Paper.class))).willReturn(Collections.singletonList(paper));

            // when
            PaperSearchResponse response = paperService.searchPapers(user, query, null, 1, "relevance");

            // then
            assertThat(response).isNotNull();
            assertThat(response.total()).isEqualTo(1);
            assertThat(response.items()).hasSize(1);
            assertThat(response.items().get(0).title()).isEqualTo("Introduction to AI");
        }

        @Test
        void 유효하지_않은_페이지_번호는_1페이지로_보정된다() {
            // given
            User user = User.builder().build();
            String query = "AI";
            int invalidPage = 0;

            Paper paper = Paper.builder()
                    .id("1")
                    .title("Introduction to AI")
                    .build();

            given(mongoTemplate.count(any(Query.class), eq(Paper.class))).willReturn(1L);
            given(mongoTemplate.find(any(Query.class), eq(Paper.class))).willReturn(Collections.singletonList(paper));

            // when
            PaperSearchResponse response = paperService.searchPapers(user, query, null, invalidPage, "relevance");

            // then
            assertThat(response).isNotNull();
            assertThat(response.page()).isEqualTo(1); // Should be corrected to 1
        }
        @Test
        void 텍스트_검색_결과가_10000건_이상일_때_isApproximate_True() {
            // given
            User user = User.builder().build();
            String query = "Big Data";
            long largeTotal = 15000L;

            Paper paper = Paper.builder()
                    .id("1")
                    .title("Big Data Analysis")
                    .build();

            given(mongoTemplate.count(any(Query.class), eq(Paper.class))).willReturn(largeTotal);
            given(mongoTemplate.find(any(Query.class), eq(Paper.class))).willReturn(Collections.singletonList(paper));

            // when
            PaperSearchResponse response = paperService.searchPapers(user, query, null, 1, "relevance");

            // then
            assertThat(response).isNotNull();
            assertThat(response.total()).isEqualTo(largeTotal);
            assertThat(response.isApproximate()).isTrue();
        }
    }
    
    @Nested
    class GetPaperDetail {

        @Test
        void 논문_상세_조회_및_조회수_증가_성공() {
            // given
            User user = User.builder().build();
            String paperId = "1";

            Paper paper = Paper.builder()
                    .id(paperId)
                    .viewCount(10)
                    .title("Test Paper")
                    .build();

            given(mongoTemplate.findAndModify(
                    any(Query.class),
                    any(org.springframework.data.mongodb.core.query.Update.class),
                    any(org.springframework.data.mongodb.core.FindAndModifyOptions.class),
                    eq(Paper.class)
            )).willReturn(paper);

            // when
            PaperDetailResponse result = paperService.getPaperDetail(user, paperId);

            // then
            assertThat(result).isNotNull();
            assertThat(result.id()).isEqualTo(paperId);
            assertThat(result.viewCount()).isEqualTo(10);
        }
    }
}
