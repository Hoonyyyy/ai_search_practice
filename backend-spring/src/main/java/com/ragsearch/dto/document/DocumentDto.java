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

    private DocumentDto(Document document) {
        this.docId = document.getDocId();
        this.filename = document.getFilename();
        this.chunkCount = document.getChunkCount();
        this.uploadedAt = document.getUploadedAt()
                .format(DateTimeFormatter.ISO_LOCAL_DATE_TIME);
    }

    public static DocumentDto from(Document document) {
        return new DocumentDto(document);
    }
}
