package com.inha.capstone.paper.controller;

import com.inha.capstone.auth.security.UserPrincipal;
import com.inha.capstone.paper.dto.PaperSearchResponse;
import com.inha.capstone.paper.model.Paper;
import com.inha.capstone.paper.service.PaperService;
import com.inha.capstone.user.domain.User;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/papers")
@RequiredArgsConstructor
public class PaperController {

    private final PaperService paperService;

    @GetMapping("/search")
    public ResponseEntity<PaperSearchResponse> searchPapers(
            @AuthenticationPrincipal UserPrincipal userPrincipal,
            @RequestParam(required = false) String q,
            @RequestParam(required = false) List<String> categories,
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "relevance") String sort
    ) {
        // User is optional for search in original code, but Service method expects it for logging history
        // If userPrincipal is null, handle it (though AuthenticationPrincipal usually implies authenticated, 
        // if endpoints are public in SecurityConfig, it might be null)
        User user = userPrincipal != null ? userPrincipal.getUser() : null;
        
        return ResponseEntity.ok(paperService.searchPapers(user, q, categories, page, sort));
    }

    @GetMapping("/{paperId}")
    public ResponseEntity<Paper> getPaperDetail(
            @AuthenticationPrincipal UserPrincipal userPrincipal,
            @PathVariable String paperId
    ) {
        User user = userPrincipal != null ? userPrincipal.getUser() : null;
        // Basic requirement: User needed for activity logging. If not logged in, maybe skip logging or log as anonymous?
        // Original code enforced user login for get_paper_detail via `deps.get_current_user` usually, 
        // but let's assume loose coupling for now.
        
        // However, if we strictly follow the original `get_paper_detail` signature `user: User`, it implies authentication is required.
        // If authentication is required, `userPrincipal` won't be null.
        
        return ResponseEntity.ok(paperService.getPaperDetail(user, paperId));
    }
}
