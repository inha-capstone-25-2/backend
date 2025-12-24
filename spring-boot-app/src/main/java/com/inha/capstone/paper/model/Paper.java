package com.inha.capstone.paper.model;

import lombok.Data;
import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.mapping.Document;
import org.springframework.data.mongodb.core.mapping.Field;

import java.time.LocalDateTime;
import java.util.List;

@Data
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

    @Data
    public static class Summary {
        private String en;
        private String ko;
    }
    
    @Data
    public static class Version {
        private String version;
        private String created;
    }
}
