package com.inha.capstone.paper.service;

import com.inha.capstone.common.exception.CustomException;
import com.inha.capstone.common.exception.ErrorCode;
import com.inha.capstone.paper.dto.PaperListItem;
import com.inha.capstone.paper.dto.PaperSearchResponse;
import com.inha.capstone.paper.model.Paper;
import com.inha.capstone.paper.model.PaperPublicationPolicy;
import com.mongodb.client.MongoClient;
import com.mongodb.client.MongoClients;
import com.mongodb.client.MongoCollection;
import com.mongodb.client.model.Indexes;
import org.bson.Document;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.springframework.data.mongodb.core.MongoTemplate;
import org.springframework.test.util.ReflectionTestUtils;
import org.testcontainers.containers.MongoDBContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

@Testcontainers
class PaperServiceVisibilityTest {

    @Container
    static final MongoDBContainer mongo = new MongoDBContainer("mongo:6");

    private static MongoClient mongoClient;
    private static MongoTemplate mongoTemplate;
    private static MongoCollection<Document> papers;

    private PaperService paperService;

    @BeforeAll
    static void 몽고디비_준비() {
        mongoClient = MongoClients.create(mongo.getReplicaSetUrl());
        mongoTemplate = new MongoTemplate(mongoClient, "paper_visibility_test");
        papers = mongoTemplate.getCollection("papers");
        papers.createIndex(Indexes.text("title"));
    }

    @AfterAll
    static void 몽고디비_연결_종료() {
        mongoClient.close();
    }

    @BeforeEach
    void 논문_준비() {
        paperService = new PaperService(null, mongoTemplate);
        papers.deleteMany(new Document());
        papers.insertMany(List.of(
                논문("ready", 5).append("categories", List.of("cs.AI", "math.ST"))
                        .append("summary", new Document("en", "English summary").append("ko", "한국어 요약")),
                논문("non-cs", 4).append("categories", List.of("math.ST")),
                논문("legacy", 3).append("title", "Algebra"),
                논문("uppercase", 2).append("categories", List.of("CS.AI")),
                논문("no-summary", 100).append("categories", List.of("math.ST", "cs.AI")),
                논문("english-only", 99).append("categories", List.of("cs.AI"))
                        .append("summary", new Document("en", "English summary")),
                논문("blank-english", 98).append("categories", List.of("cs.AI"))
                        .append("summary", new Document("en", "\t\u00a0\u3000").append("ko", "한국어 요약")),
                논문("blank-korean", 97).append("categories", List.of("cs.AI"))
                        .append("summary", new Document("en", "English summary").append("ko", " \r\n"))
        ));
    }

    @Nested
    class 검색 {

        @Test
        void 검색어_없는_조회에서_노출되는_논문만_집계하고_정렬과_페이지를_적용한다() {
            // given
            ReflectionTestUtils.setField(paperService, "requireCsSummary", true);

            // when
            PaperSearchResponse firstPage = paperService.searchPapers(null, null, null, 1, "view_count");
            PaperSearchResponse secondPage = paperService.searchPapers(null, null, null, 2, "view_count");

            // then
            assertThat(firstPage.total()).isEqualTo(4);
            assertThat(firstPage.items()).extracting(PaperListItem::id)
                    .containsExactly("ready", "non-cs", "legacy", "uppercase");
            assertThat(secondPage.total()).isEqualTo(4);
            assertThat(secondPage.items()).isEmpty();
        }

        @Test
        void 텍스트_검색에_카테고리와_요약_조건을_함께_적용한다() {
            // given
            ReflectionTestUtils.setField(paperService, "requireCsSummary", true);

            // when
            PaperSearchResponse all = paperService.searchPapers(null, "Robotics", null, 1, "view_count");
            PaperSearchResponse filtered = paperService.searchPapers(
                    null, "Robotics", List.of("math.ST"), 1, "view_count");

            // then
            assertThat(all.total()).isEqualTo(3);
            assertThat(all.items()).extracting(PaperListItem::id)
                    .containsExactly("ready", "non-cs", "uppercase");
            assertThat(filtered.total()).isEqualTo(2);
            assertThat(filtered.items()).extracting(PaperListItem::id).containsExactly("ready", "non-cs");
        }

        @Test
        void 설정_기본값에서는_요약_없는_컴퓨터과학_논문도_검색된다() {
            // when
            PaperSearchResponse result = paperService.searchPapers(null, null, List.of("cs.AI"), 1, "view_count");

            // then
            assertThat(result.total()).isEqualTo(5);
            assertThat(result.items()).extracting(PaperListItem::id).contains("no-summary");
        }
    }

    @Nested
    class 상세_조회 {

        @Test
        void 노출되는_논문은_상세가_반환되고_조회수가_증가한다() {
            // given
            ReflectionTestUtils.setField(paperService, "requireCsSummary", true);

            // when, then
            assertThat(paperService.getPaperDetail(null, "ready").viewCount()).isEqualTo(6);
            assertThat(paperService.getPaperDetail(null, "legacy").viewCount()).isEqualTo(4);
        }

        @Test
        void 공백_요약이_있는_컴퓨터과학_논문은_상세에서_숨기고_조회수를_유지한다() {
            // given
            ReflectionTestUtils.setField(paperService, "requireCsSummary", true);

            // when, then
            assertThatThrownBy(() -> paperService.getPaperDetail(null, "blank-korean"))
                    .isInstanceOfSatisfying(CustomException.class,
                            exception -> assertThat(exception.getErrorCode()).isEqualTo(ErrorCode.PAPER_NOT_FOUND));
            Paper paper = mongoTemplate.findById("blank-korean", Paper.class);
            assertThat(paper).isNotNull();
            assertThat(paper.getViewCount()).isEqualTo(97);
        }

        @Test
        void 설정_기본값에서는_요약_없는_컴퓨터과학_논문도_상세가_반환된다() {
            // when, then
            assertThat(paperService.getPaperDetail(null, "no-summary").viewCount()).isEqualTo(101);
        }
    }

    @Nested
    class 분류 {

        @Test
        void 소문자_cs_접두사로_시작하는_카테고리가_있으면_컴퓨터과학이다() {
            assertThat(PaperPublicationPolicy.isComputerScience(List.of("math.ST", "cs.AI"))).isTrue();
            assertThat(PaperPublicationPolicy.isComputerScience(List.of("CS.AI", "csAI", "xcs.AI"))).isFalse();
            assertThat(PaperPublicationPolicy.isComputerScience(List.of())).isFalse();
            assertThat(PaperPublicationPolicy.isComputerScience(null)).isFalse();
        }
    }

    private static Document 논문(String id, int viewCount) {
        return new Document("_id", id).append("title", "Robotics").append("view_count", viewCount);
    }
}
