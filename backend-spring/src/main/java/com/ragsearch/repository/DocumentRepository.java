package com.ragsearch.repository;

import com.ragsearch.domain.Document;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface DocumentRepository extends JpaRepository<Document, String> {
    /** 특정 세션이 올린 문서 (내 문서) */
    List<Document> findAllByOwnerOrderByUploadedAtDesc(String owner);
    /** owner 가 없는 문서 = 예시 문서 */
    List<Document> findAllByOwnerIsNullOrderByUploadedAtDesc();

    /** 이 세션이 올린 문서가 하나라도 있는지 (검색 범위 판단용) */
    boolean existsByOwner(String owner);
}
