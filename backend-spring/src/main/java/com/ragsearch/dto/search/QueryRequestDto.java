package com.ragsearch.dto.search;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import lombok.Getter;
import lombok.NoArgsConstructor;

@Getter
@NoArgsConstructor
public class QueryRequestDto {

    @NotBlank
    @Size(min = 1, max = 1000)
    private String question;

    @Min(1) @Max(10)
    private int topK = 4;
}
