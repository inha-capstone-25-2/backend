package com.inha.capstone.recommendation.util;

import com.inha.capstone.activity.model.UserActivity;
import com.inha.capstone.activity.repository.ActivityRepository;
import com.inha.capstone.paper.model.Paper;
import com.inha.capstone.recommendation.dto.RecommendationItem;
import com.inha.capstone.user.domain.User;
import com.inha.capstone.user.repository.UserInterestRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Sort;
import org.springframework.data.mongodb.core.MongoTemplate;
import org.springframework.data.mongodb.core.query.Criteria;
import org.springframework.data.mongodb.core.query.Query;
import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

@Slf4j
@Component
@RequiredArgsConstructor
public class RuleBasedRecommender {
    private final RuleBasedScorer scorer;
    private final UserInterestRepository userInterestRepository;
    private final ActivityRepository activityRepository;
    private final MongoTemplate mongoTemplate;

    private static final double WEIGHT_INTEREST = 0.4;
    private static final double WEIGHT_POPULARITY = 0.2;
    private static final double WEIGHT_RECENCY = 0.1;
    private static final double WEIGHT_PERSONALIZATION = 0.3;

    public List<RecommendationItem> recommend(User user, int topK, int candidateLimit) {
        // 1. Get User Interests
        List<String> userInterests = userInterestRepository.findCategoryCodesByUserId(user.getId());
        
        // 2. Get User Activity
        List<UserActivity> activities = activityRepository.findRecentViewsByUserId(user.getId(), PageRequest.of(0, 50));
        List<String> viewedPaperIds = activities.stream().map(UserActivity::getDoi).collect(Collectors.toList());
        List<String> activityCategories = activities.stream()
                .filter(a -> a.getMetadata() != null && a.getMetadata().containsKey("categories"))
                .flatMap(a -> ((List<String>) a.getMetadata().get("categories")).stream())
                .collect(Collectors.toList());

        // 3. Get Candidates
        Query query = new Query();
        if (userInterests != null && !userInterests.isEmpty()) {
            query.addCriteria(Criteria.where("categories").in(userInterests));
        }
        query.with(Sort.by(Sort.Direction.DESC, "viewCount")); // Simplified sort
        query.limit(candidateLimit);
        
        List<Paper> candidates = mongoTemplate.find(query, Paper.class);
        
        // Fallback if no specific interest papers found
        if (candidates.isEmpty()) {
            query = new Query();
            query.with(Sort.by(Sort.Direction.DESC, "viewCount"));
            query.limit(candidateLimit);
            candidates = mongoTemplate.find(query, Paper.class);
        }

        // 4. Score Candidates
        List<RecommendationItem> recommendations = new ArrayList<>();
        
        for (Paper paper : candidates) {
            double interestScore = scorer.calculateInterestScore(userInterests, paper);
            double popularityScore = scorer.calculatePopularityScore(paper);
            double recencyScore = scorer.calculateRecencyScore(paper);
            double personalizationScore = scorer.calculatePersonalizationScore(user.getId(), paper, viewedPaperIds, activityCategories);
            
            double totalScore = (interestScore * WEIGHT_INTEREST) +
                                (popularityScore * WEIGHT_POPULARITY) +
                                (recencyScore * WEIGHT_RECENCY) +
                                (personalizationScore * WEIGHT_PERSONALIZATION);
            
            RecommendationItem.ScoreBreakdown breakdown = new RecommendationItem.ScoreBreakdown(
                    interestScore,
                    popularityScore,
                    recencyScore,
                    personalizationScore
            );

            recommendations.add(new RecommendationItem(
                    null,
                    paper.getId(),
                    paper.getTitle(),
                    paper.getSummary(),
                    paper.getAuthors(),
                    paper.getCategories(),
                    null,
                    null,
                    paper.getViewCount() != null ? paper.getViewCount() : 0,
                    0,
                    paper.getUpdateDate(),
                    paper.getJournalRef(),
                    totalScore,
                    breakdown,
                    analyzeReasons(interestScore, popularityScore, personalizationScore)
            ));
        }
        
        // 5. Sort by Total Score
        recommendations.sort((r1, r2) -> Double.compare(r2.totalScore(), r1.totalScore()));
        
        return recommendations.stream().limit(topK).collect(Collectors.toList());
    }
    
    private List<String> analyzeReasons(double interestScore, double popularityScore, double personalizationScore) {
        List<String> reasons = new ArrayList<>();
        if (interestScore > 1.0) reasons.add("관심사와 관련성 높음");
        if (popularityScore > 1.0) reasons.add("인기 있는 논문");
        if (personalizationScore > 0.5) reasons.add("취향 저격");
        
        if (reasons.isEmpty()) reasons.add("추천 논문");
        return reasons;
    }
}
