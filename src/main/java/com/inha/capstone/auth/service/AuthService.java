package com.inha.capstone.auth.service;

import com.inha.capstone.auth.dto.LoginRequest;
import com.inha.capstone.auth.dto.LoginResponse;
import com.inha.capstone.auth.dto.RefreshRequest;
import com.inha.capstone.auth.dto.UserCreateRequest;
import com.inha.capstone.auth.dto.UserResponse;
import com.inha.capstone.auth.jwt.JwtTokenProvider;
import com.inha.capstone.auth.jwt.TokenValidationResult;
import com.inha.capstone.auth.repository.TokenRepository;
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
    private final TokenRepository tokenRepository;

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

        tokenRepository.saveRefreshToken(
                user.getId(),
                refreshToken,
                jwtTokenProvider.getRefreshTokenExpirationSeconds()
        );

        return LoginResponse.of(accessToken, refreshToken, jwtTokenProvider.getAccessTokenExpirationSeconds());
    }

    public LoginResponse refresh(RefreshRequest request) {
        String refreshToken = request.refreshToken();

        TokenValidationResult validationResult = jwtTokenProvider.validateToken(refreshToken);
        if (validationResult != TokenValidationResult.VALID) {
            if (validationResult == TokenValidationResult.EXPIRED) {
                throw new CustomException(ErrorCode.EXPIRED_TOKEN);
            }
            throw new CustomException(ErrorCode.INVALID_TOKEN);
        }

        Long userId = jwtTokenProvider.getUserId(refreshToken);
        String username = jwtTokenProvider.getUsername(refreshToken);

        String storedToken = tokenRepository.findRefreshToken(userId)
                .orElseThrow(() -> new CustomException(ErrorCode.INVALID_TOKEN));

        if (!storedToken.equals(refreshToken)) {
            tokenRepository.deleteRefreshToken(userId);
            throw new CustomException(ErrorCode.INVALID_TOKEN);
        }

        String newAccessToken = jwtTokenProvider.createAccessToken(username, userId);
        String newRefreshToken = jwtTokenProvider.createRefreshToken(username, userId);

        tokenRepository.saveRefreshToken(
                userId,
                newRefreshToken,
                jwtTokenProvider.getRefreshTokenExpirationSeconds()
        );

        return LoginResponse.of(newAccessToken, newRefreshToken, jwtTokenProvider.getAccessTokenExpirationSeconds());
    }

    public boolean checkUsernameExists(String username) {
        return userRepository.existsByUsername(username);
    }

    public void logout(Long userId, String accessToken) {
        tokenRepository.deleteRefreshToken(userId);

        String jti = jwtTokenProvider.getJti(accessToken);
        long remainingSeconds = jwtTokenProvider.getRemainingSeconds(accessToken);
        tokenRepository.addToBlacklist(jti, remainingSeconds);
    }

    @Transactional
    public void deleteAccount(Long userId) {
        User persistentUser = userRepository.findById(userId)
                .orElseThrow(() -> new CustomException(ErrorCode.USER_NOT_FOUND));
        userRepository.delete(persistentUser);
    }
}
