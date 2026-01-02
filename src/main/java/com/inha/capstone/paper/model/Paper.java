package com.inha.capstone.paper.model;

import lombok.AccessLevel;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;
import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.mapping.Document;
import org.springframework.data.mongodb.core.mapping.Field;

import java.time.LocalDateTime;
import java.util.List;

@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
@AllArgsConstructor(access = AccessLevel.PRIVATE)
@Builder
@Document(collection = "papers")
public class Paper {
    @Id
    private String id;
    
    private String title;
    
    private Summary summary;
    
    private String authors;
    
    private List<String> categories;
    
    @Field("update_date")
    private String updateDate;
    
    @Field("view_count")
    private Integer viewCount;
    
    @Field("journal_ref")
    private String journalRef;
    
    @Field("report_no")
    private String reportNo;
    
    private String doi;
    
    private String license;
    
    private List<Version> versions;
    
    @Field("authors_parsed")
    private List<List<String>> authorsParsed;

    @Getter
    @NoArgsConstructor(access = AccessLevel.PROTECTED)
    @AllArgsConstructor
    public static class Summary {
        private String en;
        private String ko;
    }

    @Getter
    @NoArgsConstructor(access = AccessLevel.PROTECTED)
    @AllArgsConstructor
    public static class Version {
        private String version;
        private String created;
    }
}
