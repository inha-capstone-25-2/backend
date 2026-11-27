package com.inha.capstone.recommendation.service;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.inha.capstone.recommendation.dto.RecommendationInteractionRequest;
import org.springframework.core.env.Environment;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;

import java.time.Duration;

@Service
public class RecommendationAiClient {
    private final RestClient.Builder builder;
    private final Environment environment;

    public RecommendationAiClient(RestClient.Builder builder, Environment environment) {
        this.builder = builder;
        this.environment = environment;
    }

    public byte[] recommendations(long userId, String basePaperId, int limit, int candidateK) {
        try {
            byte[] body = client().get()
                    .uri(uri -> {
                        uri.path("/recommendations/rl")
                                .queryParam("user_id", userId)
                                .queryParam("limit", limit)
                                .queryParam("candidate_k", candidateK);
                        if (basePaperId != null && !basePaperId.isBlank()) {
                            uri.queryParam("base_paper_id", basePaperId);
                        }
                        return uri.build();
                    })
                    .retrieve().body(byte[].class);
            return requireBody(body);
        } catch (RestClientException | IllegalStateException | IllegalArgumentException exception) {
            throw new RecommendationAiException();
        }
    }

    public byte[] interaction(long userId, RecommendationInteractionRequest request) {
        try {
            byte[] body = client().post()
                    .uri("/recommendations/interactions")
                    .body(new InteractionPayload(userId, request.paperId(), request.recommendationId(),
                            request.actionType(), request.dwellTime()))
                    .retrieve().body(byte[].class);
            return requireBody(body);
        } catch (RestClientException | IllegalStateException | IllegalArgumentException exception) {
            throw new RecommendationAiException();
        }
    }

    private RestClient client() {
        String baseUrl = environment.getProperty("RECOMMENDATION_AI_BASE_URL", "");
        if (baseUrl.isBlank()) {
            baseUrl = environment.getProperty("app.recommendations.ai-url", "");
        }
        if (baseUrl.isBlank()) {
            baseUrl = environment.getProperty("app.gpu-server.url", "");
        }
        if (baseUrl.isBlank() || baseUrl.startsWith("${")) {
            throw new IllegalStateException("Recommendation AI URL is missing");
        }
        var requests = new SimpleClientHttpRequestFactory();
        requests.setConnectTimeout(Duration.ofSeconds(5));
        requests.setReadTimeout(Duration.ofSeconds(20));
        return builder.clone().baseUrl(baseUrl).requestFactory(requests).build();
    }

    private byte[] requireBody(byte[] body) {
        if (body == null || body.length == 0) {
            throw new RecommendationAiException();
        }
        return body;
    }

    private record InteractionPayload(
            @JsonProperty("user_id") long userId,
            @JsonProperty("paper_id") String paperId,
            @JsonProperty("recommendation_id") String recommendationId,
            @JsonProperty("action_type") String actionType,
            @JsonProperty("dwell_time") Double dwellTime
    ) {}

    public static final class RecommendationAiException extends RuntimeException {}
}
