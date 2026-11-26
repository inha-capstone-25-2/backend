package com.inha.capstone.paper.model;

import org.springframework.data.mongodb.core.query.Criteria;

import java.util.List;
import java.util.Objects;
import java.util.regex.Pattern;

public final class PaperPublicationPolicy {

    private static final Pattern CS_CATEGORY = Pattern.compile("^cs\\.");
    private static final Pattern NONBLANK_SUMMARY = Pattern.compile("[^\\s\\p{Z}\\x{85}]");

    private PaperPublicationPolicy() {
    }

    public static boolean isComputerScience(List<String> categories) {
        return categories != null && categories.stream()
                .filter(Objects::nonNull)
                .anyMatch(CS_CATEGORY.asPredicate());
    }

    public static Criteria visibilityCriteria() {
        return new Criteria().orOperator(
                new Criteria().norOperator(Criteria.where("categories").regex(CS_CATEGORY)),
                Criteria.where("summary.en").regex(NONBLANK_SUMMARY)
                        .and("summary.ko").regex(NONBLANK_SUMMARY)
        );
    }
}
