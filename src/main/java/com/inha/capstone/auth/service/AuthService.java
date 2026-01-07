package com.inha.capstone.auth.service;

import com.inha.capstone.auth.dto.LoginRequest;
import com.inha.capstone.auth.dto.LoginResponse;
import com.inha.capstone.auth.dto.UserCreateRequest;
import com.inha.capstone.auth.dto.UserResponse;
import com.inha.capstone.auth.jwt.JwtTokenProvider;
import com.inha.capstone.common.exception.CustomException;
import com.inha.capstone.common.exception.ErrorCode;
import com.inha.capstone.user.domain.User;
import com.inha.capstone.user.repository.UserRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class AuthService {

    private final UserRepository userRepository;
    private final PasswordEncoder passwordEncoder;
    private final JwtTokenProvider jwtTokenProvider;

    @Transactional
    public UserResponse register(UserCreateRequest request) {
        if (userRepository.existsByUsername(request.username())) {
            throw new CustomException(ErrorCode.DUPLICATE_USERNAME);
        }
        if (userRepository.existsByEmail(request.email())) {
            throw new CustomException(ErrorCode.DUPLICATE_EMAIL);
        }

        User user = User.builder()
                .username(request.username())
                .email(request.email())
                .name(request.name())
                .password(passwordEncoder.encode(request.password()))
                .build();

        try {
            userRepository.save(user);
        } catch (DataIntegrityViolationException e) {
            throw new CustomException(ErrorCode.ALREADY_REGISTERED_USER);
        }

        return UserResponse.from(user);
    }

    public LoginResponse login(LoginRequest request) {
        User user = userRepository.findByUsername(request.username())
                .orElseThrow(() -> new CustomException(ErrorCode.INVALID_CREDENTIALS));

        if (!passwordEncoder.matches(request.password(), user.getPassword())) {
            throw new CustomException(ErrorCode.INVALID_CREDENTIALS);
        }

        String accessToken = jwtTokenProvider.createAccessToken(user.getUsername(), user.getId());
        String refreshToken = jwtTokenProvider.createRefreshToken(user.getUsername(), user.getId());

        return LoginResponse.of(accessToken, refreshToken, jwtTokenProvider.getAccessTokenExpirationSeconds());
    }

    public boolean checkUsernameExists(String username) {
        return userRepository.existsByUsername(username);
    }

    @Transactional
    public void logout(Long userId) {
        User persistentUser = userRepository.findById(userId)
                .orElseThrow(() -> new CustomException(ErrorCode.USER_NOT_FOUND));
        persistentUser.increaseTokenVersion();
    }

    @Transactional
    public void deleteAccount(Long userId) {
        User persistentUser = userRepository.findById(userId)
                .orElseThrow(() -> new CustomException(ErrorCode.USER_NOT_FOUND));
        userRepository.delete(persistentUser);
    }
}
