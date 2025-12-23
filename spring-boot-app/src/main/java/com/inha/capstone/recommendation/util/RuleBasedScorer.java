package com.inha.capstone.recommendation.util;

import com.inha.capstone.paper.model.Paper;
import org.springframework.stereotype.Component;

import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.time.temporal.ChronoUnit;
import java.util.List;
import java.util.Map;

@Component
public class RuleBasedScorer {

    public double calculateInterestScore(List<String> userInterests, Paper paper) {
        if (userInterests == null || userInterests.isEmpty() || paper.getCategories() == null) {
            return 0.0;
        }
        
        long matchCount = paper.getCategories().stream()
                .filter(userInterests::contains)
                .count();
        
        // Simple scoring: 1.0 per match, maybe cap it? Python logic checks for intersections.
        // Assuming Python logic: simply counts or weighted?
        // Let's implement simple intersection count for now.
        return (double) matchCount * 1.5; 
    }

    public double calculatePopularityScore(Paper paper) {
        // Based on view count
        int viewCount = paper.getViewCount() != null ? paper.getViewCount() : 0;
        return Math.log1p(viewCount) * 0.5;
    }

    public double calculateRecencyScore(Paper paper) {
        if (paper.getUpdateDate() == null) return 0.0;
        
        try {
            // Provided format usually YYYY-MM-DD
            LocalDate updateDate = LocalDate.parse(paper.getUpdateDate(), DateTimeFormatter.ISO_DATE);
            long daysDiff = ChronoUnit.DAYS.between(updateDate, LocalDate.now());
            
            if (daysDiff < 30) return 3.0;
            if (daysDiff < 90) return 2.0;
            if (daysDiff < 365) return 1.0;
            return 0.5;
        } catch (Exception e) {
            return 0.0;
        }
    }

    public double calculatePersonalizationScore(Long userId, Paper paper, List<String> viewedPaperIds, List<String> activityCategories) {
        // If user viewed this paper before
        if (viewedPaperIds != null && viewedPaperIds.contains(paper.getId())) {
            return 0.0; // Already seen, maybe lower score or filter out
        }
        
        // Match with activity categories
        if (activityCategories != null && paper.getCategories() != null) {
             long matchCount = paper.getCategories().stream()
                .filter(activityCategories::contains)
                .count();
             return (double) matchCount * 0.5;
        }
        
        return 0.0;
    }
}
