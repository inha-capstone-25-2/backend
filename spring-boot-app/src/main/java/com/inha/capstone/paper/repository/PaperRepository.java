package com.inha.capstone.paper.repository;

import com.inha.capstone.paper.model.Paper;
import org.springframework.data.mongodb.repository.MongoRepository;
import org.springframework.stereotype.Repository;

public interface PaperRepository extends MongoRepository<Paper, String> {
}
