package com.ragsearch.service;

import org.junit.jupiter.api.Test;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

class DocumentServiceSplitTextTest {

    @Test
    void chunkNeverExceedsConfiguredSize() {
        // 45자 남짓한 줄을 50개 = 약 2,250자짜리 문서를 흉내
        String text = "한 줄에 적당한 길이의 문장을 넣는다. 청킹 로직이 이 줄들을 모은다.\n".repeat(50);

        List<String> chunks = DocumentService.splitText(text, 700, 100);

        int longest = chunks.stream().mapToInt(String::length).max().orElse(0);
        System.out.println(">>> 청크 개수: " + chunks.size() + ", 최대 길이: " + longest);

        assertThat(longest).isLessThanOrEqualTo(700);
    }

    @Test 
    void longLinesRevealTheRealUpperBound() {
        // 650자짜리 긴 줄 10개 (PDF에서 문단이 한 줄로 뽑히는 상황을 흉내)
        String text = ("가".repeat(650) + "\n").repeat(10);

        List<String> chunks = DocumentService.splitText(text, 700, 100);
        
        int longest = chunks.stream().mapToInt(String::length).max().orElse(0);
        System.out.println(">>> 긴 줄 케이스 - 청크 개수: " + chunks.size() + ", 최대 길이: " + longest);

        assertThat(longest).isLessThanOrEqualTo(700);
    }
}
