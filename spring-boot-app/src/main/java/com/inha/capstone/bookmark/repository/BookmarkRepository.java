package com.inha.capstone.bookmark.repository;

import com.inha.capstone.bookmark.model.Bookmark;
import org.springframework.data.mongodb.repository.MongoRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface BookmarkRepository extends MongoRepository<Bookmark, String> {
    List<Bookmark> findByUserIdOrderByBookmarkedAtDesc(Long userId);
    Optional<Bookmark> findByUserIdAndDoi(Long userId, String doi);
}
