package com.inha.capstone.auth.repository;

import lombok.RequiredArgsConstructor;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Repository;

import java.util.Optional;
import java.util.concurrent.TimeUnit;

@Repository
@RequiredArgsConstructor
public class TokenRepository {

    private final RedisTemplate<String, Object> redisTemplate;

    private static final String REFRESH_PREFIX = "refresh:";
    private static final String BLACKLIST_PREFIX = "blacklist:";

    public void saveRefreshToken(Long userId, String token, long expirationSeconds) {
        String key = REFRESH_PREFIX + userId;
        redisTemplate.opsForValue().set(key, token, expirationSeconds, TimeUnit.SECONDS);
    }

    public Optional<String> findRefreshToken(Long userId) {
        String key = REFRESH_PREFIX + userId;
        Object value = redisTemplate.opsForValue().get(key);
        return Optional.ofNullable(value).map(Object::toString);
    }

    public void deleteRefreshToken(Long userId) {
        String key = REFRESH_PREFIX + userId;
        redisTemplate.delete(key);
    }

    public void addToBlacklist(String jti, long remainingSeconds) {
        if (remainingSeconds > 0) {
            String key = BLACKLIST_PREFIX + jti;
            redisTemplate.opsForValue().set(key, "1", remainingSeconds, TimeUnit.SECONDS);
        }
    }

    public boolean isBlacklisted(String jti) {
        String key = BLACKLIST_PREFIX + jti;
        return Boolean.TRUE.equals(redisTemplate.hasKey(key));
    }
}
