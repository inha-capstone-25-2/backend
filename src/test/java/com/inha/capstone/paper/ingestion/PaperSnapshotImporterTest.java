package com.inha.capstone.paper.ingestion;

import com.inha.capstone.paper.ingestion.PaperEnrichmentClient.Enrichment;
import com.inha.capstone.paper.ingestion.PaperEnrichmentClient.Summary;
import com.mongodb.client.MongoClient;
import com.mongodb.client.MongoClients;
import com.mongodb.client.MongoCollection;
import com.sun.net.httpserver.HttpServer;
import org.bson.Document;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.web.client.RestClient;
import org.testcontainers.containers.MongoDBContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;

import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicReference;

import static com.mongodb.client.model.Filters.eq;
import static org.assertj.core.api.Assertions.assertThat;

@Testcontainers
class PaperSnapshotImporterTest {
    @Container
    static final MongoDBContainer mongo = new MongoDBContainer("mongo:6");
    private static MongoClient client;

    private MongoCollection<Document> papers;

    @BeforeAll
    static void connect() {
        client = MongoClients.create(mongo.getReplicaSetUrl());
    }

    @AfterAll
    static void close() {
        client.close();
    }

    @BeforeEach
    void clearCollection() {
        papers = client.getDatabase("ingestion_test").getCollection("papers");
        papers.drop();
    }

    @Test
    void persistsCompleteAiResultsAndDoesNotReprocessUnchangedInputs() throws IOException {
        var received = new AtomicReference<Document>();
        var server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        server.createContext("/summarize/enrich", exchange -> {
            try (exchange) {
                received.set(Document.parse(new String(exchange.getRequestBody().readAllBytes(), StandardCharsets.UTF_8)));
                byte[] response = """
                        {"summary":{"en":"AI summary","ko":"AI 요약"},
                         "keywords":["systems"],"embedding_vector":[0.25]}
                        """.getBytes(StandardCharsets.UTF_8);
                exchange.getResponseHeaders().set("Content-Type", "application/json");
                exchange.sendResponseHeaders(200, response.length);
                exchange.getResponseBody().write(response);
            }
        });
        server.start();
        try {
            var nlp = new PaperEnrichmentClient(RestClient.builder(), "http://127.0.0.1:" + server.getAddress().getPort());
            var importer = new PaperSnapshotImporter(papers, nlp::enrich);
            String snapshot = """
                    {"id":"2401.12345","title":"CS","abstract":"Computer science","text":"Paper body","categories":"math.OC cs.LG","update_date":"2024-01-15"}
                    {"id":"2401.12346","title":"Math","abstract":"Math paper","categories":"math.OC","update_date":"2024-01-15"}
                    """;
            assertThat(importer.readSnapshot(input(snapshot))).isEqualTo(new PaperSnapshotImporter.ImportResult(2, 0, 0));
            assertThat(received.get()).isEqualTo(new Document("abstract", "Computer science").append("text", "Paper body"));
            var paper = papers.find(eq("_id", "2401.12345")).first();
            assertThat(paper.get("summary")).isEqualTo(new Document("en", "AI summary").append("ko", "AI 요약"));
            assertThat(paper.getList("keywords", String.class)).containsExactly("systems");
            assertThat(paper.getList("embedding_vector", Double.class)).containsExactly(0.25);
            assertThat(paper.getBoolean("summary_refined")).isTrue();
            assertThat(papers.find(eq("_id", "2401.12346")).first().get("summary"))
                    .isEqualTo(new Document("en", "Math paper").append("ko", null));

            received.set(null);
            assertThat(importer.readSnapshot(input(snapshot))).isEqualTo(new PaperSnapshotImporter.ImportResult(0, 2, 0));
            assertThat(received.get()).isNull();
        } finally {
            server.stop(0);
        }
    }

    @Test
    void failedAiRequestKeepsPreviousRevisionAndRetriesOnNextImport() throws IOException {
        papers.insertOne(new Document("_id", "2401.12345")
                .append("categories", List.of("cs.LG")).append("update_date", "2024-01-15")
                .append("abstract", "Old abstract").append("view_count", 12)
                .append("summary", new Document("en", "Previous summary").append("ko", "이전 요약")));
        String snapshot = """
                {"id":"2401.12345","abstract":"Changed abstract","categories":"cs.LG","update_date":"2024-02-15"}
                {"id":"2401.12346","abstract":"New abstract","categories":"cs.AI","update_date":"2024-02-15"}
                """;
        var attempts = new AtomicInteger();
        var importer = new PaperSnapshotImporter(papers, (abstractText, fullText) -> {
            if (attempts.incrementAndGet() <= 2) {
                throw new IllegalStateException("NLP unavailable");
            }
            return new Enrichment(new Summary("New summary", "새 요약"), List.of(), List.of(0.25));
        });

        assertThat(importer.readSnapshot(input(snapshot))).isEqualTo(new PaperSnapshotImporter.ImportResult(0, 0, 2));
        assertThat(papers.countDocuments()).isEqualTo(1);
        assertThat(papers.find(eq("_id", "2401.12345")).first().getString("abstract")).isEqualTo("Old abstract");

        assertThat(importer.readSnapshot(input(snapshot))).isEqualTo(new PaperSnapshotImporter.ImportResult(2, 0, 0));
        var updated = papers.find(eq("_id", "2401.12345")).first();
        assertThat(updated.getString("abstract")).isEqualTo("Changed abstract");
        assertThat(updated.getInteger("view_count")).isEqualTo(12);
        assertThat(attempts).hasValue(4);
    }

    @Test
    void keepsCompleteLegacySummaryAndRejectsIncompleteNewSummary() throws IOException {
        papers.insertOne(new Document("_id", "2401.12345").append("update_date", "2024-01-15")
                .append("summary", new Document("en", "Legacy summary").append("ko", "기존 요약")));
        var attempts = new AtomicInteger();
        var importer = new PaperSnapshotImporter(papers, (abstractText, fullText) -> {
            attempts.incrementAndGet();
            return new Enrichment(new Summary("Only English", "  "), List.of(), List.of(0.25));
        });
        String snapshot = """
                {"id":"2401.12345","abstract":"Old abstract","categories":"cs.LG","update_date":"2024-01-15"}
                {"id":"2401.12346","abstract":"New abstract","categories":"cs.AI","update_date":"2024-01-15"}
                """;

        assertThat(importer.readSnapshot(input(snapshot))).isEqualTo(new PaperSnapshotImporter.ImportResult(1, 0, 1));
        assertThat(attempts).hasValue(1);
        assertThat(papers.countDocuments()).isEqualTo(1);
        assertThat(papers.find(eq("_id", "2401.12345")).first().get("summary"))
                .isEqualTo(new Document("en", "Legacy summary").append("ko", "기존 요약"));
    }

    private static ByteArrayInputStream input(String snapshot) {
        return new ByteArrayInputStream(snapshot.getBytes(StandardCharsets.UTF_8));
    }
}
