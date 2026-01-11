package com.inha.capstone.auth.jwt;

import com.inha.capstone.auth.repository.TokenRepository;
import com.inha.capstone.auth.security.JwtAuthenticationToken;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpHeaders;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Component;
import org.springframework.util.StringUtils;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.util.List;

@Slf4j
@Component
@RequiredArgsConstructor
public class JwtAuthenticationFilter extends OncePerRequestFilter {

    private final JwtTokenProvider jwtTokenProvider;
    private final TokenRepository tokenRepository;

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain filterChain)
            throws ServletException, IOException {
        String authorizationHeader = request.getHeader(HttpHeaders.AUTHORIZATION);
        String jwt = jwtTokenProvider.extractBearerToken(authorizationHeader);

        if (StringUtils.hasText(jwt)) {
            TokenValidationResult validationResult = jwtTokenProvider.validateToken(jwt);

            if (validationResult == TokenValidationResult.VALID) {
                String jti = jwtTokenProvider.getJti(jwt);

                if (tokenRepository.isBlacklisted(jti)) {
                    log.debug("블랙리스트에 등록된 토큰입니다.");
                    filterChain.doFilter(request, response);
                    return;
                }

                Long userId = jwtTokenProvider.getUserId(jwt);
                String username = jwtTokenProvider.getUsername(jwt);

                JwtAuthenticationToken authentication = new JwtAuthenticationToken(
                        userId,
                        username,
                        List.of(new SimpleGrantedAuthority("ROLE_USER"))
                );

                SecurityContextHolder.getContext().setAuthentication(authentication);
            }
        }

        filterChain.doFilter(request, response);
    }
}
