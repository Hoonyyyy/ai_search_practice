package com.ragsearch.dto.document;

import com.ragsearch.domain.Document;
import lombok.Getter;

import java.time.format.DateTimeFormatter;

@Getter
public class DocumentDto {

    private final String docId;
    private final String filename;
    private final int chunkCount;
    private final String uploadedAt;

    /** owner 가 없는 문서 = 예시 문서. 화면에서 배지를 달고 삭제 버튼을 감춘다. */
    private final boolean sample;

    private DocumentDto(Document document) {
        this.docId = document.getDocId();
        this.filename = document.getFilename();
        this.chunkCount = document.getChunkCount();
        this.uploadedAt = document.getUploadedAt()
                .format(DateTimeFormatter.ISO_LOCAL_DATE_TIME);
        this.sample = document.getOwner() == null;
    }

    public static DocumentDto from(Document document) {
        return new DocumentDto(document);
    }
}
