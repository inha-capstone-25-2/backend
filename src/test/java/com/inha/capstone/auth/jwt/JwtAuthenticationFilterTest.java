package com.inha.capstone.auth.jwt;

import com.inha.capstone.auth.repository.TokenRepository;
import com.inha.capstone.auth.security.JwtAuthenticationToken;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.http.HttpHeaders;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.mock.web.MockHttpServletResponse;
import org.springframework.security.core.context.SecurityContextHolder;

import java.io.IOException;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.BDDMockito.given;
import static org.mockito.BDDMockito.then;
import static org.mockito.Mockito.never;

@ExtendWith(MockitoExtension.class)
class JwtAuthenticationFilterTest {

    @Mock
    private JwtTokenProvider jwtTokenProvider;

    @Mock
    private TokenRepository tokenRepository;

    @Mock
    private FilterChain filterChain;

    private JwtAuthenticationFilter jwtAuthenticationFilter;

    private MockHttpServletRequest request;
    private MockHttpServletResponse response;

    @BeforeEach
    void setUp() {
        jwtAuthenticationFilter = new JwtAuthenticationFilter(jwtTokenProvider, tokenRepository);
        request = new MockHttpServletRequest();
        response = new MockHttpServletResponse();
        SecurityContextHolder.clearContext();
    }

    @Nested
    class 인증_성공 {

        @Test
        void 유효한_토큰으로_인증_성공() throws ServletException, IOException {
            // given
            String token = "valid-token";
            String authorizationHeader = "Bearer " + token;
            String jti = "token-jti";
            Long userId = 1L;
            String username = "testuser";

            request.addHeader(HttpHeaders.AUTHORIZATION, authorizationHeader);

            given(jwtTokenProvider.extractBearerToken(authorizationHeader)).willReturn(token);
            given(jwtTokenProvider.validateToken(token)).willReturn(TokenValidationResult.VALID);
            given(jwtTokenProvider.getJti(token)).willReturn(jti);
            given(tokenRepository.isBlacklisted(jti)).willReturn(false);
            given(jwtTokenProvider.getUserId(token)).willReturn(userId);
            given(jwtTokenProvider.getUsername(token)).willReturn(username);

            // when
            jwtAuthenticationFilter.doFilterInternal(request, response, filterChain);

            // then
            var authentication = SecurityContextHolder.getContext().getAuthentication();
            assertThat(authentication).isInstanceOf(JwtAuthenticationToken.class);

            JwtAuthenticationToken jwtAuth = (JwtAuthenticationToken) authentication;
            assertThat(jwtAuth.getUserId()).isEqualTo(userId);
            assertThat(jwtAuth.getUsername()).isEqualTo(username);
            assertThat(jwtAuth.isAuthenticated()).isTrue();

            then(filterChain).should().doFilter(request, response);
        }
    }

    @Nested
    class 인증_실패 {

        @Test
        void 블랙리스트에_등록된_토큰은_인증_실패() throws ServletException, IOException {
            // given
            String token = "blacklisted-token";
            String authorizationHeader = "Bearer " + token;
            String jti = "blacklisted-jti";

            request.addHeader(HttpHeaders.AUTHORIZATION, authorizationHeader);

            given(jwtTokenProvider.extractBearerToken(authorizationHeader)).willReturn(token);
            given(jwtTokenProvider.validateToken(token)).willReturn(TokenValidationResult.VALID);
            given(jwtTokenProvider.getJti(token)).willReturn(jti);
            given(tokenRepository.isBlacklisted(jti)).willReturn(true);

            // when
            jwtAuthenticationFilter.doFilterInternal(request, response, filterChain);

            // then
            assertThat(SecurityContextHolder.getContext().getAuthentication()).isNull();
            then(jwtTokenProvider).should(never()).getUserId(token);
            then(filterChain).should().doFilter(request, response);
        }

        @Test
        void 유효하지_않은_토큰은_인증_실패() throws ServletException, IOException {
            // given
            String token = "invalid-token";
            String authorizationHeader = "Bearer " + token;

            request.addHeader(HttpHeaders.AUTHORIZATION, authorizationHeader);

            given(jwtTokenProvider.extractBearerToken(authorizationHeader)).willReturn(token);
            given(jwtTokenProvider.validateToken(token)).willReturn(TokenValidationResult.INVALID_SIGNATURE);

            // when
            jwtAuthenticationFilter.doFilterInternal(request, response, filterChain);

            // then
            assertThat(SecurityContextHolder.getContext().getAuthentication()).isNull();
            then(tokenRepository).should(never()).isBlacklisted(anyString());
            then(filterChain).should().doFilter(request, response);
        }

        @Test
        void 만료된_토큰은_인증_실패() throws ServletException, IOException {
            // given
            String token = "expired-token";
            String authorizationHeader = "Bearer " + token;

            request.addHeader(HttpHeaders.AUTHORIZATION, authorizationHeader);

            given(jwtTokenProvider.extractBearerToken(authorizationHeader)).willReturn(token);
            given(jwtTokenProvider.validateToken(token)).willReturn(TokenValidationResult.EXPIRED);

            // when
            jwtAuthenticationFilter.doFilterInternal(request, response, filterChain);

            // then
            assertThat(SecurityContextHolder.getContext().getAuthentication()).isNull();
            then(tokenRepository).should(never()).isBlacklisted(anyString());
            then(filterChain).should().doFilter(request, response);
        }

        @Test
        void Authorization_헤더가_없으면_인증_건너뜀() throws ServletException, IOException {
            // given
            given(jwtTokenProvider.extractBearerToken(null)).willReturn(null);

            // when
            jwtAuthenticationFilter.doFilterInternal(request, response, filterChain);

            // then
            assertThat(SecurityContextHolder.getContext().getAuthentication()).isNull();
            then(jwtTokenProvider).should(never()).validateToken(anyString());
            then(filterChain).should().doFilter(request, response);
        }

        @Test
        void Bearer_형식이_아니면_인증_건너뜀() throws ServletException, IOException {
            // given
            String authorizationHeader = "Basic some-token";
            request.addHeader(HttpHeaders.AUTHORIZATION, authorizationHeader);

            given(jwtTokenProvider.extractBearerToken(authorizationHeader)).willReturn(null);

            // when
            jwtAuthenticationFilter.doFilterInternal(request, response, filterChain);

            // then
            assertThat(SecurityContextHolder.getContext().getAuthentication()).isNull();
            then(jwtTokenProvider).should(never()).validateToken(anyString());
            then(filterChain).should().doFilter(request, response);
        }
    }
}
