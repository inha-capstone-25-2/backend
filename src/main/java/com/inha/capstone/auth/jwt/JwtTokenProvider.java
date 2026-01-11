package com.inha.capstone.auth.jwt;

import io.jsonwebtoken.Claims;
import io.jsonwebtoken.ExpiredJwtException;
import io.jsonwebtoken.MalformedJwtException;
import io.jsonwebtoken.UnsupportedJwtException;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.io.Decoders;
import io.jsonwebtoken.security.Keys;
import io.jsonwebtoken.security.SignatureException;
import jakarta.annotation.PostConstruct;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import org.springframework.util.StringUtils;

import javax.crypto.SecretKey;
import java.util.Date;
import java.util.UUID;

@Slf4j
@Component
public class JwtTokenProvider {

    private static final String BEARER_PREFIX = "Bearer ";

    private static final String CLAIM_USER_ID = "uid";

    @Value("${jwt.secret}")
    private String secretKey;

    @Value("${jwt.access-expiration}")
    private long accessTokenExpirationMinutes;

    @Value("${jwt.refresh-expiration}")
    private long refreshTokenExpirationDays;

    private SecretKey key;

    @PostConstruct
    public void init() {
        byte[] keyBytes = Decoders.BASE64.decode(secretKey);
        this.key = Keys.hmacShaKeyFor(keyBytes);
    }

    public String createAccessToken(String username, Long userId) {
        long expirationMillis = accessTokenExpirationMinutes * 60 * 1000;
        return createToken(username, userId, expirationMillis);
    }

    public String createRefreshToken(String username, Long userId) {
        long expirationMillis = refreshTokenExpirationDays * 24 * 60 * 60 * 1000;
        return createToken(username, userId, expirationMillis);
    }

    private String createToken(String username, Long userId, long expirationMillis) {
        Date now = new Date();
        Date validity = new Date(now.getTime() + expirationMillis);

        return Jwts.builder()
                .id(UUID.randomUUID().toString())
                .subject(username)
                .claim(CLAIM_USER_ID, userId)
                .issuedAt(now)
                .expiration(validity)
                .signWith(key)
                .compact();
    }

    public String extractBearerToken(String authorizationHeader) {
        if (StringUtils.hasText(authorizationHeader) && authorizationHeader.startsWith(BEARER_PREFIX)) {
            return authorizationHeader.substring(BEARER_PREFIX.length());
        }
        return null;
    }

    public TokenValidationResult validateToken(String token) {
        try {
            Jwts.parser().verifyWith(key).build().parseSignedClaims(token);
            return TokenValidationResult.VALID;
        } catch (ExpiredJwtException e) {
            log.warn("만료된 토큰입니다.");
            return TokenValidationResult.EXPIRED;
        } catch (SignatureException e) {
            log.warn("토큰 서명이 유효하지 않습니다.");
            return TokenValidationResult.INVALID_SIGNATURE;
        } catch (MalformedJwtException | IllegalArgumentException e) {
            log.warn("토큰 형식이 올바르지 않습니다.");
            return TokenValidationResult.MALFORMED;
        } catch (UnsupportedJwtException e) {
            log.warn("지원하지 않는 토큰 형식입니다.");
            return TokenValidationResult.UNSUPPORTED;
        }
    }

    public Claims getClaims(String token) {
        return Jwts.parser()
                .verifyWith(key)
                .build()
                .parseSignedClaims(token)
                .getPayload();
    }

    public String getUsername(String token) {
        return getClaims(token).getSubject();
    }

    public String getJti(String token) {
        return getClaims(token).getId();
    }

    public Long getUserId(String token) {
        return getClaims(token).get(CLAIM_USER_ID, Long.class);
    }

    public long getAccessTokenExpirationSeconds() {
        return accessTokenExpirationMinutes * 60;
    }

    public long getRefreshTokenExpirationSeconds() {
        return refreshTokenExpirationDays * 24 * 60 * 60;
    }

    public long getRemainingSeconds(String token) {
        Date expiration = getClaims(token).getExpiration();
        long remainingMillis = expiration.getTime() - System.currentTimeMillis();
        return Math.max(0, remainingMillis / 1000);
    }
}
