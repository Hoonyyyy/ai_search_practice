package com.ragsearch.dto.search;

import jakarta.validation.constraints.*;
import lombok.Getter;
import lombok.NoArgsConstructor;

@Getter
@NoArgsConstructor
public class FeedbackRequestDto {

    @NotBlank
    private String queryId;

    @DecimalMin("1.0") @DecimalMax("5.0")
    private double score;
}
