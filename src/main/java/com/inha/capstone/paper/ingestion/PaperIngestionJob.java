package com.inha.capstone.paper.ingestion;

import com.inha.capstone.paper.model.Paper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.context.annotation.Configuration;
import org.springframework.core.env.Environment;
import org.springframework.data.mongodb.core.MongoTemplate;
import org.springframework.scheduling.annotation.EnableScheduling;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.web.client.RestClient;
import software.amazon.awssdk.services.s3.S3Client;
import software.amazon.awssdk.services.s3.model.GetObjectRequest;

import java.io.IOException;
import java.io.InputStream;
import java.net.URI;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.util.zip.GZIPInputStream;

@Slf4j
@Configuration(proxyBeanMethods = false)
@EnableScheduling
@RequiredArgsConstructor
class PaperIngestionJob {
    private final MongoTemplate mongo;
    private final Environment environment;
    private final RestClient.Builder http;
    private final ObjectProvider<S3Client> s3;

    @Scheduled(cron = "${app.papers.ingestion.cron:-}", zone = "Asia/Seoul")
    public void importSnapshot() {
        URI source = URI.create(environment.getRequiredProperty("app.papers.ingestion.source"));
        String nlpUrl = environment.getProperty("app.papers.ingestion.nlp-url", "");
        if (nlpUrl.isBlank()) {
            nlpUrl = environment.getRequiredProperty("app.gpu-server.url");
        }
        var nlp = new PaperEnrichmentClient(http, nlpUrl);
        var importer = new PaperSnapshotImporter(mongo.getCollection(mongo.getCollectionName(Paper.class)), nlp::enrich);

        log.info("Starting arXiv snapshot import");
        try {
            var result = read(source, importer);
            if (result.failed() > 0) {
                log.warn("arXiv import completed with errors: {} saved, {} unchanged, {} failed",
                        result.saved(), result.unchanged(), result.failed());
            } else {
                log.info("arXiv import complete: {} saved, {} unchanged", result.saved(), result.unchanged());
            }
        } catch (IOException exception) {
            throw new IllegalStateException("Could not read the arXiv snapshot", exception);
        }
    }

    private PaperSnapshotImporter.ImportResult read(URI source, PaperSnapshotImporter importer) throws IOException {
        if ("file".equals(source.getScheme())) {
            return readFile(Path.of(source), source.getPath().endsWith(".gz"), importer);
        }
        if (!"s3".equals(source.getScheme()) || source.getHost() == null
                || source.getPath() == null || source.getPath().length() < 2) {
            throw new IllegalArgumentException("Snapshot source must be a file: or s3: URI with a file path");
        }

        Path snapshot = Files.createTempFile("arxiv-snapshot-", ".download");
        try {
            var request = GetObjectRequest.builder()
                    .bucket(source.getHost())
                    .key(source.getPath().substring(1))
                    .build();
            try (InputStream input = s3.getObject().getObject(request)) {
                Files.copy(input, snapshot, StandardCopyOption.REPLACE_EXISTING);
            }
            return readFile(snapshot, source.getPath().endsWith(".gz"), importer);
        } finally {
            Files.deleteIfExists(snapshot);
        }
    }

    private PaperSnapshotImporter.ImportResult readFile(Path path, boolean gzip, PaperSnapshotImporter importer)
            throws IOException {
        try (InputStream raw = Files.newInputStream(path)) {
            if (!gzip) {
                return importer.readSnapshot(raw);
            }
            try (InputStream input = new GZIPInputStream(raw)) {
                return importer.readSnapshot(input);
            }
        }
    }
}
