package com.inha.capstone.paper.service;

import com.inha.capstone.paper.dto.PaperListItem;
import com.inha.capstone.paper.dto.PaperSearchResponse;
import com.inha.capstone.paper.model.Paper;
import com.inha.capstone.paper.repository.PaperRepository;
import com.inha.capstone.user.domain.User;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;
import org.springframework.data.mongodb.core.MongoTemplate;
import org.springframework.data.mongodb.core.query.Criteria;
import org.springframework.data.mongodb.core.query.Query;
import org.springframework.data.mongodb.core.query.TextCriteria;
import org.springframework.data.mongodb.core.query.TextQuery;
import org.springframework.data.mongodb.core.query.Update;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
public class PaperService {
    private final PaperRepository paperRepository;
    private final MongoTemplate mongoTemplate;


    public PaperSearchResponse searchPapers(User user, String query, List<String> categories, int page, String sortBy) {
        int pageSize = 10;
        Pageable pageable = PageRequest.of(page - 1, pageSize, getSort(sortBy));
        
        long total;
        List<Paper> papers;
        boolean isApproximate = false;

        if (query != null && !query.isEmpty()) {
            // Text Search
            TextCriteria criteria = TextCriteria.forDefaultLanguage().matching(query);
            Query textQuery = TextQuery.queryText(criteria).sortByScore();
            
            if (categories != null && !categories.isEmpty()) {
                textQuery.addCriteria(Criteria.where("categories").in(categories));
            }
            
            total = mongoTemplate.count(textQuery, Paper.class);
            textQuery.with(pageable);
            papers = mongoTemplate.find(textQuery, Paper.class);
            
        } else {
            // Category Filter or All
            Query simpleQuery = new Query();
            if (categories != null && !categories.isEmpty()) {
                simpleQuery.addCriteria(Criteria.where("categories").in(categories));
            }
            
            total = mongoTemplate.count(simpleQuery, Paper.class);
            simpleQuery.with(pageable);
            papers = mongoTemplate.find(simpleQuery, Paper.class);
            
            if (total >= 10000) {
                isApproximate = true;
            }
        }

        List<PaperListItem> items = papers.stream()
                .map(PaperListItem::from)
                .collect(Collectors.toList());

        int totalPages = total > 0 ? (int) Math.ceil((double) total / pageSize) : 0;

        return PaperSearchResponse.builder()
                .page(page)
                .pageSize(pageSize)
                .total(total)
                .totalPages(totalPages)
                .hasNext(page < totalPages)
                .hasPrev(page > 1)
                .isApproximate(isApproximate)
                .items(items)
                .build();
    }

    public Paper getPaperDetail(User user, String paperId) {
        // Atomic increment using MongoTemplate
        Query query = new Query(Criteria.where("id").is(paperId));
        Update update = new Update().inc("viewCount", 1);
        

        Paper paper = mongoTemplate.findAndModify(
            query,
            update,
            org.springframework.data.mongodb.core.FindAndModifyOptions.options().returnNew(true),
            Paper.class
        );

        if (paper == null) {
            throw new RuntimeException("Paper not found with id: " + paperId);
        }
        
        // TODO: Log activity (view)
        
        return paper;
    }

    private Sort getSort(String sortBy) {
        if ("view_count".equals(sortBy)) {
            return Sort.by(Sort.Direction.DESC, "viewCount").and(Sort.by(Sort.Direction.DESC, "updateDate"));
        } else if ("update_date".equals(sortBy)) {
            return Sort.by(Sort.Direction.DESC, "updateDate");
        }
        return Sort.by(Sort.Direction.DESC, "updateDate");
    }
}
