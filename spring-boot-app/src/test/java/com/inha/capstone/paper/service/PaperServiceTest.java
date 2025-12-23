package com.inha.capstone.paper.service;

import com.inha.capstone.paper.dto.PaperSearchResponse;
import com.inha.capstone.paper.model.Paper;
import com.inha.capstone.paper.repository.PaperRepository;
import com.inha.capstone.user.domain.User;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.data.domain.Pageable;
import org.springframework.data.mongodb.core.MongoTemplate;
import org.springframework.data.mongodb.core.query.Query;

import java.util.Collections;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class PaperServiceTest {

    @Mock
    private PaperRepository paperRepository;

    @Mock
    private MongoTemplate mongoTemplate;

    @InjectMocks
    private PaperService paperService;

    @Test
    void searchPapers_shouldReturnResults_whenQueryIsProvided() {
        // Given
        User user = User.builder().build();
        String query = "AI";
        
        Paper paper = new Paper();
        paper.setId("1");
        paper.setTitle("Introduction to AI");
        
        when(mongoTemplate.count(any(Query.class), eq(Paper.class))).thenReturn(1L);
        when(mongoTemplate.find(any(Query.class), eq(Paper.class))).thenReturn(Collections.singletonList(paper));

        // When
        PaperSearchResponse response = paperService.searchPapers(user, query, null, 1, "relevance");

        // Then
        assertNotNull(response);
        assertEquals(1, response.total());
        assertEquals(1, response.items().size());
        assertEquals("Introduction to AI", response.items().get(0).title());
    }
}
