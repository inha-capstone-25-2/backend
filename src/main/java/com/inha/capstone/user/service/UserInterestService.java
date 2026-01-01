package com.inha.capstone.user.service;

import com.inha.capstone.category.model.Category;
import com.inha.capstone.category.repository.CategoryRepository;
import com.inha.capstone.user.domain.User;
import com.inha.capstone.user.domain.UserInterest;
import com.inha.capstone.user.dto.UserInterestDto;
import com.inha.capstone.user.repository.UserInterestRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.Collections;
import java.util.List;
import java.util.Set;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class UserInterestService {

    private final UserInterestRepository userInterestRepository;
    private final CategoryRepository categoryRepository;

    @Transactional
    public List<String> addInterests(User user, List<String> categoryCodes) {
        if (categoryCodes == null || categoryCodes.isEmpty()) {
            return Collections.emptyList();
        }

        // 1. Find valid categories
        List<Category> validCategories = categoryRepository.findByCodeIn(categoryCodes);
        if (validCategories.isEmpty()) {
            return Collections.emptyList();
        }

        // 2. Find existing interests to avoid duplicates
        List<UserInterest> existingInterests = userInterestRepository.findByUserAndCategoryIn(user, validCategories);
        Set<String> existingCategoryCodes = existingInterests.stream()
                .map(ui -> ui.getCategory().getCode())
                .collect(Collectors.toSet());

        // 3. Save new interests
        List<UserInterest> newInterests = validCategories.stream()
                .filter(category -> !existingCategoryCodes.contains(category.getCode()))
                .map(category -> UserInterest.create(user, category))
                .collect(Collectors.toList());

        if (!newInterests.isEmpty()) {
            userInterestRepository.saveAll(newInterests);
        }
        
        // Return updated list of codes
        return listInterests(user).getCategories();
    }

    public UserInterestDto.InterestListResponse listInterests(User user) {
        List<String> codes = userInterestRepository.findCategoryCodesByUserId(user.getId());
        return new UserInterestDto.InterestListResponse(codes);
    }

    @Transactional
    public UserInterestDto.InterestRemovalResult removeInterests(User user, List<String> categoryCodes) {
        if (categoryCodes == null || categoryCodes.isEmpty()) {
            return new UserInterestDto.InterestRemovalResult(0);
        }

        List<Category> categories = categoryRepository.findByCodeIn(categoryCodes);
        if (categories.isEmpty()) {
            return new UserInterestDto.InterestRemovalResult(0);
        }
        
        // Count before delete for reference (optional, or just rely on delete result size if needed)
        List<UserInterest> toDelete = userInterestRepository.findByUserAndCategoryIn(user, categories);
        int deleteCount = toDelete.size();

        if (deleteCount > 0) {
            userInterestRepository.deleteAll(toDelete);
        }
        
        return new UserInterestDto.InterestRemovalResult(deleteCount);
    }
}
