package com.inha.capstone.paper.ingestion;

import com.fasterxml.jackson.annotation.JsonProperty;
import org.bson.Document;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.web.client.RestClient;

import java.time.Duration;
import java.util.List;

final class PaperEnrichmentClient {
    private final RestClient client;

    PaperEnrichmentClient(RestClient.Builder builder, String baseUrl) {
        var requests = new SimpleClientHttpRequestFactory();
        requests.setConnectTimeout(Duration.ofSeconds(5));
        requests.setReadTimeout(Duration.ofSeconds(65));
        client = builder.clone().baseUrl(baseUrl).requestFactory(requests).build();
    }

    Enrichment enrich(String abstractText, String fullText) {
        Enrichment result = client.post()
                .uri("/summarize/enrich")
                .body(new EnrichmentRequest(abstractText, fullText))
                .retrieve()
                .body(Enrichment.class);
        if (result == null || result.summary() == null || !result.summary().isComplete()
                || result.keywords() == null || result.keywords().stream().anyMatch(value -> value == null)
                || result.embedding() == null || result.embedding().isEmpty()
                || result.embedding().stream().anyMatch(value -> value == null || !Double.isFinite(value))) {
            throw new IllegalStateException("NLP server returned an incomplete enrichment");
        }
        return result;
    }

    private record EnrichmentRequest(@JsonProperty("abstract") String abstractText, String text) {}

    record Enrichment(Summary summary, List<String> keywords,
                      @JsonProperty("embedding_vector") List<Double> embedding) {}

    record Summary(String en, String ko) {
        boolean isComplete() {
            return en != null && !en.isBlank() && ko != null && !ko.isBlank();
        }

        Document toDocument() {
            return new Document("en", en).append("ko", ko);
        }
    }
}
