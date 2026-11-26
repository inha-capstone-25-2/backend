package com.inha.capstone.paper.ingestion;

import com.inha.capstone.paper.ingestion.PaperEnrichmentClient.Enrichment;
import com.inha.capstone.paper.ingestion.PaperEnrichmentClient.Summary;
import com.inha.capstone.paper.model.PaperPublicationPolicy;
import com.mongodb.client.MongoCollection;
import lombok.extern.slf4j.Slf4j;
import org.bson.Document;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.UUID;
import java.util.function.BiFunction;

import static com.mongodb.client.model.Filters.and;
import static com.mongodb.client.model.Filters.eq;
import static com.mongodb.client.model.Filters.in;
import static com.mongodb.client.model.Projections.exclude;

@Slf4j
final class PaperSnapshotImporter {
    private static final int READ_BATCH_SIZE = 200;
    private static final String REVISION = "arxiv_ingest_revision";

    private final MongoCollection<Document> papers;
    private final BiFunction<String, String, Enrichment> enrich;

    PaperSnapshotImporter(MongoCollection<Document> papers, BiFunction<String, String, Enrichment> enrich) {
        this.papers = papers;
        this.enrich = enrich;
    }

    ImportResult readSnapshot(InputStream input) throws IOException {
        var totals = new ImportResult(0, 0, 0);
        var batch = new ArrayList<Document>(READ_BATCH_SIZE);
        var reader = new BufferedReader(new InputStreamReader(input, StandardCharsets.UTF_8));
        long lineNumber = 0;
        for (String line; (line = reader.readLine()) != null;) {
            lineNumber++;
            if (line.isBlank()) {
                continue;
            }
            try {
                batch.add(toPaper(Document.parse(line)));
            } catch (RuntimeException exception) {
                log.warn("Invalid arXiv snapshot record at line {} ({})",
                        lineNumber, exception.getClass().getSimpleName());
                totals = totals.add(new ImportResult(0, 0, 1));
            }
            if (batch.size() == READ_BATCH_SIZE) {
                totals = totals.add(saveBatch(batch));
                batch.clear();
            }
        }
        return totals.add(saveBatch(batch));
    }

    private ImportResult saveBatch(List<Document> batch) {
        if (batch.isEmpty()) {
            return new ImportResult(0, 0, 0);
        }
        Map<String, Document> stored = new HashMap<>();
        papers.find(in("_id", batch.stream().map(paper -> paper.getString("_id")).toList()))
                .projection(exclude("embedding_vector", "keywords"))
                .forEach(paper -> stored.put(paper.getString("_id"), paper));

        int saved = 0;
        int unchanged = 0;
        int failed = 0;
        for (Document incoming : batch) {
            String id = incoming.getString("_id");
            Document current = stored.get(id);
            try {
                Document update = prepareUpdate(incoming, current);
                if (update == null) {
                    unchanged++;
                    continue;
                }
                update.put(REVISION, UUID.randomUUID().toString());
                save(id, current, update);
                Document savedPaper = current == null ? new Document("_id", id) : current;
                savedPaper.putAll(update);
                stored.put(id, savedPaper);
                saved++;
            } catch (RuntimeException exception) {
                log.warn("Could not import arXiv paper {} ({})", id, exception.getClass().getSimpleName());
                failed++;
            }
        }
        return new ImportResult(saved, unchanged, failed);
    }

    private Document prepareUpdate(Document incoming, Document current) {
        String updateDate = incoming.getString("update_date");
        String storedDate = current == null ? null : current.getString("update_date");
        if (updateDate != null && storedDate != null && storedDate.compareTo(updateDate) > 0) {
            return null;
        }

        Document update = new Document(incoming);
        update.remove("_id");
        String abstractText = incoming.getString("abstract");
        String fullText = incoming.getString("text");
        if (fullText == null && current != null) {
            fullText = current.getString("text");
        }

        Summary previousSummary = readSummary(current);
        boolean complete = previousSummary != null && previousSummary.isComplete();
        boolean sameSource = current != null && Objects.equals(fullText, current.getString("text"))
                && (current.getString("abstract") == null
                    ? updateDate != null && updateDate.equals(storedDate)
                    : Objects.equals(abstractText, current.getString("abstract")));

        if (PaperPublicationPolicy.isComputerScience(incoming.getList("categories", String.class))) {
            if (!complete || !sameSource) {
                if (abstractText == null && fullText == null) {
                    throw new IllegalArgumentException("CS paper has no source text");
                }
                Enrichment result = enrich.apply(abstractText == null ? "" : abstractText, fullText);
                if (result == null || result.summary() == null || !result.summary().isComplete()) {
                    throw new IllegalStateException("AI enrichment did not return both summaries");
                }
                update.put("summary", result.summary().toDocument());
                update.put("keywords", result.keywords());
                update.put("embedding_vector", result.embedding());
                update.put("summary_refined", true);
            }
        } else if (!complete && abstractText != null && (previousSummary == null || !sameSource)) {
            update.put("summary", new Summary(abstractText, null).toDocument());
        }

        if (current != null && update.entrySet().stream().allMatch(
                entry -> Objects.equals(current.get(entry.getKey()), entry.getValue()))) {
            return null;
        }
        return update;
    }

    private void save(String id, Document current, Document update) {
        if (current == null) {
            papers.insertOne(new Document(update).append("_id", id));
            return;
        }
        var filter = and(eq("_id", id), eq(REVISION, current.get(REVISION)));
        if (papers.updateOne(filter, new Document("$set", update)).getMatchedCount() == 0) {
            throw new IllegalStateException("Paper was updated by another import");
        }
    }

    private static Summary readSummary(Document current) {
        if (current != null && current.get("summary") instanceof Document summary) {
            return new Summary(summary.getString("en"), summary.getString("ko"));
        }
        return null;
    }

    private static Document toPaper(Document source) {
        String id = source.getString("id");
        if (id == null || id.isBlank()) {
            throw new IllegalArgumentException("Snapshot record has no arXiv ID");
        }
        String categories = source.getString("categories");
        if (categories == null || categories.isBlank()) {
            throw new IllegalArgumentException("Snapshot record has no arXiv categories");
        }

        var paper = new Document("_id", id).append("categories", List.of(categories.strip().split("\\s+")));
        for (String field : List.of("title", "authors", "abstract", "text", "update_date", "doi", "license",
                "versions", "authors_parsed")) {
            Object value = source.get(field);
            if (value instanceof String text && (field.equals("abstract") || field.equals("text"))) {
                value = text.isBlank() ? null : text.strip();
            }
            if (value != null) {
                paper.append(field, value);
            }
        }
        if (source.get("journal-ref") != null) {
            paper.append("journal_ref", source.get("journal-ref"));
        }
        if (source.get("report-no") != null) {
            paper.append("report_no", source.get("report-no"));
        }
        return paper;
    }

    record ImportResult(int saved, int unchanged, int failed) {
        ImportResult add(ImportResult other) {
            return new ImportResult(saved + other.saved, unchanged + other.unchanged, failed + other.failed);
        }
    }
}
