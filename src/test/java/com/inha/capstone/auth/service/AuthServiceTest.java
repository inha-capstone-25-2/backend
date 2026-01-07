package com.inha.capstone.auth.service;

import com.inha.capstone.auth.dto.LoginRequest;
import com.inha.capstone.auth.dto.TokenResponse;
import com.inha.capstone.auth.dto.UserCreateRequest;
import com.inha.capstone.auth.dto.UserResponse;
import com.inha.capstone.auth.jwt.JwtTokenProvider;
import com.inha.capstone.common.exception.CustomException;
import com.inha.capstone.common.exception.ErrorCode;
import com.inha.capstone.user.domain.User;
import com.inha.capstone.user.repository.UserRepository;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.security.authentication.BadCredentialsException;
import org.springframework.security.crypto.password.PasswordEncoder;

import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.BDDMockito.given;
import static org.mockito.BDDMockito.then;
import static org.mockito.Mockito.never;

@ExtendWith(MockitoExtension.class)
class AuthServiceTest {

    @Mock
    private UserRepository userRepository;

    @Mock
    private PasswordEncoder passwordEncoder;

    @Mock
    private JwtTokenProvider jwtTokenProvider;

    @InjectMocks
    private AuthService authService;

    @Nested
    class Register {

        @Test
        void 회원가입_성공() {
            // given
            UserCreateRequest request = new UserCreateRequest(
                    "new@example.com", "newuser", "New User", "password1234"
            );

            given(userRepository.existsByUsername("newuser")).willReturn(false);
            given(userRepository.existsByEmail("new@example.com")).willReturn(false);
            given(passwordEncoder.encode("password1234")).willReturn("encodedPassword");
            given(userRepository.save(any(User.class))).willAnswer(invocation -> invocation.getArgument(0));

            // when
            UserResponse response = authService.register(request);

            // then
            assertThat(response.email()).isEqualTo("new@example.com");
            assertThat(response.username()).isEqualTo("newuser");

            then(userRepository).should().existsByUsername("newuser");
            then(userRepository).should().existsByEmail("new@example.com");
            then(passwordEncoder).should().encode("password1234");
            then(userRepository).should().save(any(User.class));
        }

        @Test
        void 중복된_이메일로_가입시_실패() {
            // given
            UserCreateRequest request = new UserCreateRequest(
                    "existing@example.com", "newuser", "New User", "password1234"
            );

            given(userRepository.existsByUsername("newuser")).willReturn(false);
            given(userRepository.existsByEmail("existing@example.com")).willReturn(true);

            // when & then
            assertThatThrownBy(() -> authService.register(request))
                    .isInstanceOf(CustomException.class)
                    .hasFieldOrPropertyWithValue("errorCode", ErrorCode.DUPLICATE_EMAIL);

            then(userRepository).should().existsByUsername("newuser");
            then(userRepository).should().existsByEmail("existing@example.com");
            then(userRepository).should(never()).save(any(User.class));
        }

        @Test
        void 중복된_아이디로_가입시_실패() {
            // given
            UserCreateRequest request = new UserCreateRequest(
                    "new@example.com", "existinguser", "New User", "password1234"
            );

            given(userRepository.existsByUsername("existinguser")).willReturn(true);

            // when & then
            assertThatThrownBy(() -> authService.register(request))
                    .isInstanceOf(CustomException.class)
                    .hasFieldOrPropertyWithValue("errorCode", ErrorCode.DUPLICATE_USERNAME);

            then(userRepository).should().existsByUsername("existinguser");
            then(userRepository).should(never()).existsByEmail(anyString());
            then(userRepository).should(never()).save(any(User.class));
        }

        @Test
        void 동시성_이슈로_인한_중복_가입_시도_시_예외가_발생한다() {
            // given
            UserCreateRequest request = new UserCreateRequest(
                    "race@example.com", "raceuser", "Race User", "password1234"
            );

            given(userRepository.existsByUsername("raceuser")).willReturn(false);
            given(userRepository.existsByEmail("race@example.com")).willReturn(false);
            given(passwordEncoder.encode("password1234")).willReturn("encodedPassword");
            
            // save 호출 시 DataIntegrityViolationException 발생
            given(userRepository.save(any(User.class)))
                    .willThrow(new DataIntegrityViolationException("Unique constraint violation"));

            // when & then
            assertThatThrownBy(() -> authService.register(request))
                    .isInstanceOf(CustomException.class)
                    .hasFieldOrPropertyWithValue("errorCode", ErrorCode.ALREADY_REGISTERED_USER);

            then(userRepository).should().save(any(User.class));
        }
    }

    @Nested
    class Login {

        @Test
        void 로그인_성공() {
            // given
            LoginRequest request = new LoginRequest("testuser", "password1234");
            User user = User.builder()
                    .email("test@example.com")
                    .username("testuser")
                    .name("Test User")
                    .password("encodedPassword")
                    .build();

            given(userRepository.findByUsername("testuser")).willReturn(Optional.of(user));
            given(passwordEncoder.matches("password1234", "encodedPassword")).willReturn(true);
            given(jwtTokenProvider.createAccessToken("testuser", 0)).willReturn("jwt-token");

            // when
            TokenResponse response = authService.login(request);

            // then
            assertThat(response.accessToken()).isEqualTo("jwt-token");

            then(userRepository).should().findByUsername("testuser");
            then(passwordEncoder).should().matches("password1234", "encodedPassword");
            then(jwtTokenProvider).should().createAccessToken("testuser", 0);
        }

        @Test
        void 존재하지_않는_아이디로_로그인_실패() {
            // given
            LoginRequest request = new LoginRequest("unknown", "password");

            given(userRepository.findByUsername("unknown")).willReturn(Optional.empty());

            // when & then
            assertThatThrownBy(() -> authService.login(request))
                    .isInstanceOf(BadCredentialsException.class)
                    .hasMessage("잘못된 아이디 또는 비밀번호입니다.");

            then(userRepository).should().findByUsername("unknown");
            then(passwordEncoder).should(never()).matches(anyString(), anyString());
            then(jwtTokenProvider).should(never()).createAccessToken(anyString(), anyInt());
        }

        @Test
        void 비밀번호_불일치_실패() {
            // given
            LoginRequest request = new LoginRequest("testuser", "wrongpassword");
            User user = User.builder()
                    .email("test@example.com")
                    .username("testuser")
                    .name("Test User")
                    .password("encodedPassword")
                    .build();

            given(userRepository.findByUsername("testuser")).willReturn(Optional.of(user));
            given(passwordEncoder.matches("wrongpassword", "encodedPassword")).willReturn(false);

            // when & then
            assertThatThrownBy(() -> authService.login(request))
                    .isInstanceOf(BadCredentialsException.class)
                    .hasMessage("잘못된 아이디 또는 비밀번호입니다.");

            then(userRepository).should().findByUsername("testuser");
            then(passwordEncoder).should().matches("wrongpassword", "encodedPassword");
            then(jwtTokenProvider).should(never()).createAccessToken(anyString(), anyInt());
        }
    }

    @Nested
    class CheckUsernameExists {

        @Test
        void 존재하는_닉네임이면_true를_리턴한다() {
            // given
            given(userRepository.existsByUsername("existing")).willReturn(true);

            // when
            boolean result = authService.checkUsernameExists("existing");

            // then
            assertThat(result).isTrue();
            then(userRepository).should().existsByUsername("existing");
        }

        @Test
        void 존재하지_않는_닉네임이면_false를_리턴한다() {
            // given
            given(userRepository.existsByUsername("unknown")).willReturn(false);

            // when
            boolean result = authService.checkUsernameExists("unknown");

            // then
            assertThat(result).isFalse();
            then(userRepository).should().existsByUsername("unknown");
        }
    }

    @Nested
    class Logout {

        @Test
        void 로그아웃_성공() {
            // given
            Long userId = 1L;
            User persistentUser = User.builder()
                    .email("test@example.com")
                    .username("testuser")
                    .name("Test")
                    .password("pw")
                    .build();
            // tokenVersion은 기본값(0)일 것임

            given(userRepository.findById(userId)).willReturn(Optional.of(persistentUser));

            // when
            authService.logout(userId);

            // then
            assertThat(persistentUser.getTokenVersion()).isEqualTo(1);
            then(userRepository).should().findById(userId);
        }

        @Test
        void 존재하지_않는_사용자_로그아웃_실패() {
            // given
            Long userId = 999L;
            given(userRepository.findById(userId)).willReturn(Optional.empty());

            // when & then
            assertThatThrownBy(() -> authService.logout(userId))
                    .isInstanceOf(CustomException.class)
                    .hasFieldOrPropertyWithValue("errorCode", ErrorCode.USER_NOT_FOUND);

            then(userRepository).should().findById(userId);
        }
    }

    @Nested
    class DeleteAccount {

        @Test
        void 계정_삭제_성공() {
            // given
            Long userId = 1L;
            User persistentUser = User.builder()
                    .email("test@example.com")
                    .username("testuser")
                    .name("Test")
                    .password("pw")
                    .build();

            given(userRepository.findById(userId)).willReturn(Optional.of(persistentUser));

            // when
            authService.deleteAccount(userId);

            // then
            then(userRepository).should().findById(userId);
            then(userRepository).should().delete(persistentUser);
        }

        @Test
        void 존재하지_않는_사용자_계정_삭제_실패() {
            // given
            Long userId = 999L;
            given(userRepository.findById(userId)).willReturn(Optional.empty());

            // when & then
            assertThatThrownBy(() -> authService.deleteAccount(userId))
                    .isInstanceOf(CustomException.class)
                    .hasFieldOrPropertyWithValue("errorCode", ErrorCode.USER_NOT_FOUND);

            then(userRepository).should().findById(userId);
            then(userRepository).should(never()).delete(any(User.class));
        }
    }
}
