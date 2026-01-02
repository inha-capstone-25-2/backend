package com.inha.capstone.recommendation.repository;

import com.inha.capstone.recommendation.model.RecommendationEvent;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.mongodb.repository.MongoRepository;
import org.springframework.stereotype.Repository;

@Repository
public interface RecommendationEventRepository extends MongoRepository<RecommendationEvent, String> {
    Page<RecommendationEvent> findBySessionId(String sessionId, Pageable pageable);
    Page<RecommendationEvent> findByUserId(Long userId, Pageable pageable);
}
