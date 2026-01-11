package com.inha.capstone.user.service;

import com.inha.capstone.category.model.Category;
import com.inha.capstone.category.repository.CategoryRepository;
import com.inha.capstone.user.domain.User;
import com.inha.capstone.user.domain.UserInterest;
import com.inha.capstone.user.dto.UserInterestListResponse;
import com.inha.capstone.user.dto.UserInterestRemovalResponse;
import com.inha.capstone.user.repository.UserInterestRepository;
import com.inha.capstone.user.repository.UserRepository;
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
    private final UserRepository userRepository;

    @Transactional
    public List<String> addInterests(Long userId, List<String> categoryCodes) {
        if (categoryCodes == null || categoryCodes.isEmpty()) {
            return Collections.emptyList();
        }

        List<Category> validCategories = categoryRepository.findByCodeIn(categoryCodes);
        if (validCategories.isEmpty()) {
            return Collections.emptyList();
        }

        List<UserInterest> existingInterests = userInterestRepository.findByUserIdAndCategoryIn(userId, validCategories);
        Set<String> existingCategoryCodes = existingInterests.stream()
                .map(ui -> ui.getCategory().getCode())
                .collect(Collectors.toSet());

        User userReference = userRepository.getReferenceById(userId);
        List<UserInterest> newInterests = validCategories.stream()
                .filter(category -> !existingCategoryCodes.contains(category.getCode()))
                .map(category -> UserInterest.create(userReference, category))
                .toList();

        if (!newInterests.isEmpty()) {
            userInterestRepository.saveAll(newInterests);
        }

        return listInterests(userId).categories();
    }

    public UserInterestListResponse listInterests(Long userId) {
        List<String> codes = userInterestRepository.findCategoryCodesByUserId(userId);
        return new UserInterestListResponse(codes);
    }

    @Transactional
    public UserInterestRemovalResponse removeInterests(Long userId, List<String> categoryCodes) {
        if (categoryCodes == null || categoryCodes.isEmpty()) {
            return new UserInterestRemovalResponse(0);
        }

        List<Category> categories = categoryRepository.findByCodeIn(categoryCodes);
        if (categories.isEmpty()) {
            return new UserInterestRemovalResponse(0);
        }

        List<UserInterest> toDelete = userInterestRepository.findByUserIdAndCategoryIn(userId, categories);
        int deleteCount = toDelete.size();

        if (deleteCount > 0) {
            userInterestRepository.deleteAll(toDelete);
        }

        return new UserInterestRemovalResponse(deleteCount);
    }
}
