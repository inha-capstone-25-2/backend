package com.inha.capstone.user.dto;

import java.util.List;

public record UserInterestAddRequest(
    List<String> categoryCodes
) {}
