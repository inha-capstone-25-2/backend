package com.inha.capstone.user.repository;

import com.inha.capstone.user.domain.UserInterest;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.List;

public interface UserInterestRepository extends JpaRepository<UserInterest, Long> {

    @Query("SELECT c.code FROM UserInterest ui JOIN ui.category c WHERE ui.user.id = :userId")
    List<String> findCategoryCodesByUserId(@Param("userId") Long userId);

    @Query("SELECT ui FROM UserInterest ui WHERE ui.user.id = :userId AND ui.category IN :categories")
    List<UserInterest> findByUserIdAndCategoryIn(@Param("userId") Long userId, @Param("categories") List<com.inha.capstone.category.model.Category> categories);
}
