package com.inha.capstone.activity.repository;

import com.inha.capstone.activity.model.UserActivity;
import org.springframework.data.domain.Pageable;
import org.springframework.data.mongodb.repository.MongoRepository;
import org.springframework.data.mongodb.repository.Query;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface ActivityRepository extends MongoRepository<UserActivity, String> {
    
    @Query(value = "{ 'user_id' : ?0, 'activity_type' : 'view' }", sort = "{ 'timestamp' : -1 }")
    List<UserActivity> findRecentViewsByUserId(Long userId, Pageable pageable);
}
