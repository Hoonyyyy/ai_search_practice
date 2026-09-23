package com.ragsearch.repository;

import com.ragsearch.domain.Document;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.time.LocalDateTime;
import java.util.List;

@Repository
public interface DocumentRepository extends JpaRepository<Document, String> {
    /** 특정 세션이 올린 문서 (내 문서) */
    List<Document> findAllByOwnerOrderByUploadedAtDesc(String owner);
    /** owner 가 없는 문서 = 예시 문서 */
    List<Document> findAllByOwnerIsNullOrderByUploadedAtDesc();

    /** 아직 살아 있는 내 문서 (만료 시각 이후에 올라온 것) */
    List<Document> findAllByOwnerAndUploadedAtAfterOrderByUploadedAtDesc(String owner, LocalDateTime after);

    /** 아직 살아 있는 내 문서가 있는지 (검색 범위 판단용) */
    boolean existsByOwnerAndUploadedAtAfter(String owner, LocalDateTime after);

    /** 수명이 지난 익명 문서. 예시 문서(owner = null)는 제외된다 */
    List<Document> findAllByOwnerIsNotNullAndUploadedAtBefore(LocalDateTime before);
}
