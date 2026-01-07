package com.inha.capstone.auth.jwt;

import io.jsonwebtoken.Claims;
import io.jsonwebtoken.JwtException;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.io.Decoders;
import io.jsonwebtoken.security.Keys;
import jakarta.annotation.PostConstruct;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import javax.crypto.SecretKey;
import java.util.Date;
import java.util.UUID;

@Component
public class JwtTokenProvider {

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

    public boolean validateToken(String token) {
        try {
            Jwts.parser().verifyWith(key).build().parseSignedClaims(token);
            return true;
        } catch (JwtException | IllegalArgumentException e) {
        }
        return false;
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
}
