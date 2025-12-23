package com.inha.capstone.recommendation.repository;

import com.inha.capstone.recommendation.model.RecommendationLog;
import org.springframework.data.mongodb.repository.MongoRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface RecommendationRepository extends MongoRepository<RecommendationLog, String> {
    List<RecommendationLog> findByUserIdOrderByRecommendedAtDesc(Long userId);
}
