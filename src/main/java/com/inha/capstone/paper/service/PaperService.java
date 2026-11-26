package com.inha.capstone.paper.service;

import com.inha.capstone.common.exception.CustomException;
import com.inha.capstone.common.exception.ErrorCode;
import com.inha.capstone.paper.dto.PaperDetailResponse;
import com.inha.capstone.paper.dto.PaperListItem;
import com.inha.capstone.paper.dto.PaperSearchResponse;
import com.inha.capstone.paper.model.Paper;
import com.inha.capstone.paper.model.PaperPublicationPolicy;
import com.inha.capstone.paper.repository.PaperRepository;
import com.inha.capstone.user.domain.User;
import lombok.RequiredArgsConstructor;
import org.springframework.beans.factory.annotation.Value;
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

import java.util.List;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
public class PaperService {

    private final PaperRepository paperRepository;
    private final MongoTemplate mongoTemplate;

    @Value("${app.papers.require-cs-summary:false}")
    private boolean requireCsSummary;

    public PaperSearchResponse searchPapers(User user, String query, List<String> categories, int page, String sortBy) {
        int pageSize = 10;

        if (page < 1) {
            page = 1;
        }
        Pageable pageable = PageRequest.of(page - 1, pageSize, getSort(sortBy));

        Query searchQuery = query != null && !query.isEmpty()
                ? TextQuery.queryText(TextCriteria.forDefaultLanguage().matching(query)).sortByScore()
                : new Query();
        if (categories != null && !categories.isEmpty()) {
            searchQuery.addCriteria(Criteria.where("categories").in(categories));
        }
        applyVisibility(searchQuery);

        long total = mongoTemplate.count(searchQuery, Paper.class);
        List<Paper> papers = mongoTemplate.find(searchQuery.with(pageable), Paper.class);
        boolean isApproximate = total >= 10000;

        List<PaperListItem> items = papers.stream()
                .map(PaperListItem::from)
                .collect(Collectors.toList());

        int totalPages = total > 0 ? (int) Math.ceil((double) total / pageSize) : 0;

        return new PaperSearchResponse(
                page,
                pageSize,
                total,
                totalPages,
                page < totalPages,
                page > 1,
                isApproximate,
                items
        );
    }

    public PaperDetailResponse getPaperDetail(User user, String paperId) {
        // Atomic increment using MongoTemplate
        Query query = new Query(Criteria.where("id").is(paperId));
        applyVisibility(query);
        Update update = new Update().inc("viewCount", 1);

        Paper paper = mongoTemplate.findAndModify(
            query,
            update,
            org.springframework.data.mongodb.core.FindAndModifyOptions.options().returnNew(true),
            Paper.class
        );

        if (paper == null) {
            throw new CustomException(ErrorCode.PAPER_NOT_FOUND);
        }

        // TODO: Log activity (view)

        return PaperDetailResponse.from(paper);
    }

    private void applyVisibility(Query query) {
        if (requireCsSummary) {
            query.addCriteria(PaperPublicationPolicy.visibilityCriteria());
        }
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
