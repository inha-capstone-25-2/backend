package com.inha.capstone.common.dto;

import org.springframework.data.domain.Slice;

import java.util.List;
import java.util.function.Function;

public record SliceResponse<T>(
        List<T> content,
        int size,
        boolean hasNext
) {

    public static <T> SliceResponse<T> from(Slice<T> slice) {
        return new SliceResponse<>(
                slice.getContent(),
                slice.getSize(),
                slice.hasNext()
        );
    }

    public static <T, R> SliceResponse<R> of(Slice<T> slice, Function<T, R> mapper) {
        List<R> content = slice.getContent().stream()
                .map(mapper)
                .toList();

        return new SliceResponse<>(
                content,
                slice.getSize(),
                slice.hasNext()
        );
    }
}
