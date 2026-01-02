package com.inha.capstone.user.service;

import com.inha.capstone.category.model.Category;
import com.inha.capstone.category.repository.CategoryRepository;
import com.inha.capstone.user.domain.User;
import com.inha.capstone.user.domain.UserInterest;
import com.inha.capstone.user.dto.UserInterestListResponse;
import com.inha.capstone.user.dto.UserInterestRemovalResponse;
import com.inha.capstone.user.repository.UserInterestRepository;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.test.util.ReflectionTestUtils;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyList;
import static org.mockito.BDDMockito.given;
import static org.mockito.BDDMockito.then;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;

@ExtendWith(MockitoExtension.class)
class UserInterestServiceTest {

    @Mock
    private UserInterestRepository userInterestRepository;

    @Mock
    private CategoryRepository categoryRepository;

    @InjectMocks
    private UserInterestService userInterestService;

    @Test
    @DisplayName("관심사 추가 성공 - 중복 제외하고 저장")
    void addInterests_Success() {
        // given
        User user = User.builder().username("test").build();
        List<String> codes = List.of("CS.AI", "CS.CV");

        Category c1 = mock(Category.class);
        given(c1.getCode()).willReturn("CS.AI");
        Category c2 = mock(Category.class);
        given(c2.getCode()).willReturn("CS.CV");
        List<Category> foundCategories = List.of(c1, c2);

        given(categoryRepository.findByCodeIn(codes)).willReturn(foundCategories);
        given(userInterestRepository.findByUserAndCategoryIn(user, foundCategories)).willReturn(Collections.emptyList());
        
        // Mocking return for listInterests
        given(userInterestRepository.findCategoryCodesByUserId(user.getId())).willReturn(codes);

        // when
        List<String> result = userInterestService.addInterests(user, codes);

        // then
        then(userInterestRepository).should().saveAll(anyList());
        assertThat(result).containsExactlyInAnyOrder("CS.AI", "CS.CV");
    }

    @Test
    @DisplayName("관심사 추가 - 존재하지 않는 카테고리는 무시")
    void addInterests_IgnoreInvalid() {
        // given
        User user = User.builder().username("test").build();
        List<String> codes = List.of("INVALID");

        given(categoryRepository.findByCodeIn(codes)).willReturn(Collections.emptyList());

        // when
        List<String> result = userInterestService.addInterests(user, codes);

        // then
        assertThat(result).isEmpty();
        then(userInterestRepository).should(never()).findByUserAndCategoryIn(any(), anyList());
        then(userInterestRepository).should(never()).saveAll(any());
    }

    @Test
    @DisplayName("관심사 목록 조회")
    void listInterests() {
        // given
        User user = User.builder().username("test").build();
        ReflectionTestUtils.setField(user, "id", 1L);

        List<String> expectedCodes = List.of("CS.AI");
        given(userInterestRepository.findCategoryCodesByUserId(1L)).willReturn(expectedCodes);

        // when
        UserInterestListResponse response = userInterestService.listInterests(user);

        // then
        assertThat(response.categories()).isEqualTo(expectedCodes);
    }

    @Test
    @DisplayName("관심사 삭제")
    void removeInterests() {
        // given
        User user = User.builder().username("test").build();
        List<String> codes = List.of("CS.AI");
        Category c1 = mock(Category.class);
        given(c1.getCode()).willReturn("CS.AI");
        List<Category> foundCategories = List.of(c1);

        UserInterest ui = UserInterest.create(user, c1);
        List<UserInterest> interestsToDelete = List.of(ui);

        given(categoryRepository.findByCodeIn(codes)).willReturn(foundCategories);
        given(userInterestRepository.findByUserAndCategoryIn(user, foundCategories)).willReturn(interestsToDelete);

        // when
        UserInterestRemovalResponse result = userInterestService.removeInterests(user, codes);

        // then
        assertThat(result.removedCount()).isEqualTo(1);
        then(userInterestRepository).should().deleteAll(interestsToDelete);
    }
}
