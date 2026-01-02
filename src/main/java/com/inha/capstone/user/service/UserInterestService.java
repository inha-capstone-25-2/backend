package com.inha.capstone.user.service;

import com.inha.capstone.category.model.Category;
import com.inha.capstone.category.repository.CategoryRepository;
import com.inha.capstone.user.domain.User;
import com.inha.capstone.user.domain.UserInterest;
import com.inha.capstone.user.dto.UserInterestListResponse;
import com.inha.capstone.user.dto.UserInterestRemovalResponse;
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

        List<Category> validCategories = categoryRepository.findByCodeIn(categoryCodes);
        if (validCategories.isEmpty()) {
            return Collections.emptyList();
        }

        List<UserInterest> existingInterests = userInterestRepository.findByUserAndCategoryIn(user, validCategories);
        Set<String> existingCategoryCodes = existingInterests.stream()
                .map(ui -> ui.getCategory().getCode())
                .collect(Collectors.toSet());

        List<UserInterest> newInterests = validCategories.stream()
                .filter(category -> !existingCategoryCodes.contains(category.getCode()))
                .map(category -> UserInterest.create(user, category))
                .toList();

        if (!newInterests.isEmpty()) {
            userInterestRepository.saveAll(newInterests);
        }

        return listInterests(user).categories();
    }

    public UserInterestListResponse listInterests(User user) {
        List<String> codes = userInterestRepository.findCategoryCodesByUserId(user.getId());
        return new UserInterestListResponse(codes);
    }

    @Transactional
    public UserInterestRemovalResponse removeInterests(User user, List<String> categoryCodes) {
        if (categoryCodes == null || categoryCodes.isEmpty()) {
            return new UserInterestRemovalResponse(0);
        }

        List<Category> categories = categoryRepository.findByCodeIn(categoryCodes);
        if (categories.isEmpty()) {
            return new UserInterestRemovalResponse(0);
        }

        List<UserInterest> toDelete = userInterestRepository.findByUserAndCategoryIn(user, categories);
        int deleteCount = toDelete.size();

        if (deleteCount > 0) {
            userInterestRepository.deleteAll(toDelete);
        }

        return new UserInterestRemovalResponse(deleteCount);
    }
}
