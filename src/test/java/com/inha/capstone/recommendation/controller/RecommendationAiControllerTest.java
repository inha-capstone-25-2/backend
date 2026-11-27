package com.inha.capstone.recommendation.controller;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.inha.capstone.auth.security.JwtAuthenticationToken;
import com.inha.capstone.common.advice.ApiResponseAdvice;
import com.inha.capstone.common.exception.GlobalExceptionHandler;
import com.inha.capstone.recommendation.service.RecommendationAiClient;
import com.sun.net.httpserver.HttpServer;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.core.env.MapPropertySource;
import org.springframework.core.env.StandardEnvironment;
import org.springframework.http.MediaType;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.web.method.annotation.CurrentSecurityContextArgumentResolver;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;
import org.springframework.web.client.RestClient;

import java.io.IOException;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.util.Map;
import java.util.List;
import java.util.concurrent.atomic.AtomicReference;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

class RecommendationAiControllerTest {
    private final ObjectMapper mapper = new ObjectMapper();
    private final AtomicReference<String> upstreamRequest = new AtomicReference<>();
    private HttpServer server;
    private MockMvc mvc;
    private int upstreamStatus;
    private String upstreamResponse;

    @BeforeEach
    void setUp() throws IOException {
        server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        server.createContext("/recommendations", exchange -> {
            String body = new String(exchange.getRequestBody().readAllBytes(), StandardCharsets.UTF_8);
            upstreamRequest.set(exchange.getRequestMethod() + " " + exchange.getRequestURI() + " " + body);
            byte[] response = upstreamResponse.getBytes(StandardCharsets.UTF_8);
            exchange.getResponseHeaders().set("Content-Type", "application/json");
            exchange.sendResponseHeaders(upstreamStatus, response.length);
            exchange.getResponseBody().write(response);
            exchange.close();
        });
        server.start();
        upstreamStatus = 200;
        upstreamResponse = "{}";

        var environment = new StandardEnvironment();
        environment.getPropertySources().addFirst(new MapPropertySource("test", Map.of(
                "app.gpu-server.url", "http://127.0.0.1:" + server.getAddress().getPort())));
        JwtAuthenticationToken authentication = new JwtAuthenticationToken(42L, "user", List.of());
        SecurityContextHolder.getContext().setAuthentication(authentication);
        mvc = MockMvcBuilders.standaloneSetup(new RecommendationAiController(
                        new RecommendationAiClient(RestClient.builder(), environment)))
                .setCustomArgumentResolvers(new CurrentSecurityContextArgumentResolver())
                .setControllerAdvice(new ApiResponseAdvice(), new GlobalExceptionHandler())
                .build();
    }

    @AfterEach
    void tearDown() {
        SecurityContextHolder.clearContext();
        server.stop(0);
    }

    @Test
    void rlForwardsPrincipalAndPreservesTopLevelRecommendationId() throws Exception {
        upstreamResponse = "{\"recommendation_id\":\"rec-12\",\"recommendations\":[{\"paper_id\":\"paper-1\"}]}";

        String response = mvc.perform(get("/api/recommendations/rl")
                        .param("base_paper_id", "paper-0")
                        .param("limit", "8")
                        .param("candidate_k", "120"))
                .andExpect(status().isOk()).andReturn().getResponse().getContentAsString();

        assertThat(response).isEqualTo(upstreamResponse);
        assertThat(upstreamRequest.get()).isEqualTo("GET /recommendations/rl?user_id=42&limit=8&candidate_k=120&base_paper_id=paper-0 ");
    }

    @Test
    void interactionUsesPrincipalAndSameRecommendationId() throws Exception {
        upstreamResponse = "{\"recommendation_id\":\"rec-12\",\"accepted\":true}";
        String response = mvc.perform(post("/api/recommendations/interactions")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"paper_id\":\"paper-1\",\"recommendation_id\":\"rec-12\",\"user_id\":999}"))
                .andExpect(status().isOk()).andReturn().getResponse().getContentAsString();

        assertThat(response).isEqualTo(upstreamResponse);
        JsonNode sent = mapper.readTree(upstreamRequest.get().split(" ", 3)[2]);
        assertThat(sent.get("user_id").asLong()).isEqualTo(42);
        assertThat(sent.get("paper_id").asText()).isEqualTo("paper-1");
        assertThat(sent.get("recommendation_id").asText()).isEqualTo("rec-12");
        assertThat(sent.get("action_type").asText()).isEqualTo("click");
    }

    @Test
    void rejectsInvalidInputBeforeUpstreamCall() throws Exception {
        mvc.perform(get("/api/recommendations/rl").param("limit", "51"))
                .andExpect(status().isBadRequest());
        mvc.perform(post("/api/recommendations/interactions")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"paper_id\":\"paper-1\",\"recommendation_id\":3,\"dwell_time\":-1}"))
                .andExpect(status().isBadRequest());
        assertThat(upstreamRequest.get()).isNull();
    }

    @Test
    void hidesUpstreamFailure() throws Exception {
        upstreamStatus = 500;
        upstreamResponse = "{\"secret\":\"upstream details\"}";
        String response = mvc.perform(get("/api/recommendations/rl"))
                .andExpect(status().isBadGateway()).andReturn().getResponse().getContentAsString();

        assertThat(response).contains("BAD_GATEWAY").doesNotContain("upstream details");
        assertThat(upstreamRequest.get()).isEqualTo("GET /recommendations/rl?user_id=42&limit=6&candidate_k=100 ");
    }
}
