package com.inha.capstone.paper.controller;

import com.inha.capstone.auth.security.UserPrincipal;
import com.inha.capstone.paper.dto.PaperDetailResponse;
import com.inha.capstone.paper.dto.PaperSearchResponse;
import com.inha.capstone.paper.service.PaperService;
import com.inha.capstone.user.domain.User;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/api/papers")
@RequiredArgsConstructor
public class PaperController {

    private final PaperService paperService;

    @GetMapping
    public ResponseEntity<PaperSearchResponse> searchPapers(
            @AuthenticationPrincipal UserPrincipal userPrincipal,
            @RequestParam(required = false) String q,
            @RequestParam(required = false) List<String> categories,
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "relevance") String sort
    ) {
        User user = userPrincipal != null ? userPrincipal.getUser() : null;
        
        return ResponseEntity.ok(paperService.searchPapers(user, q, categories, page, sort));
    }

    @GetMapping("/{paperId}")
    public ResponseEntity<PaperDetailResponse> getPaperDetail(
            @AuthenticationPrincipal UserPrincipal userPrincipal,
            @PathVariable String paperId
    ) {
        User user = userPrincipal != null ? userPrincipal.getUser() : null;


        return ResponseEntity.ok(paperService.getPaperDetail(user, paperId));
    }
}
