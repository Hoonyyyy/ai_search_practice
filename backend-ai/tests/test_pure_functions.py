"""2단계: 외부 의존성(Ollama/Qdrant/Groq) 없이 테스트 가능한 순수 함수들.

핵심 아이디어: 입력 -> 출력만 검증한다. 네트워크 호출이 없는 함수를 골랐다.
"""
from services.llm_service import _build_prompt, _messages, SYSTEM_PROMPT
from repositories.vector_repository import _to_dict


def test_build_prompt_includes_question_and_chunk_content():
    chunks = [{"content": "이력서 내용 일부"}]

    prompt = _build_prompt("나이가 몇 살이야?", chunks)

    assert "나이가 몇 살이야?" in prompt
    assert "이력서 내용 일부" in prompt
    assert "[문서 1]" in prompt


def test_build_prompt_numbers_multiple_chunks_in_order():
    chunks = [{"content": "첫 번째 청크"}, {"content": "두 번째 청크"}]

    prompt = _build_prompt("질문", chunks)

    assert prompt.index("[문서 1]") < prompt.index("[문서 2]")
    assert "첫 번째 청크" in prompt
    assert "두 번째 청크" in prompt


def test_messages_has_system_prompt_then_user_question():
    messages = _messages("질문", [{"content": "내용"}])

    assert messages[0] == {"role": "system", "content": SYSTEM_PROMPT}
    assert messages[1]["role"] == "user"
    assert "질문" in messages[1]["content"]


def test_to_dict_perfect_match_has_zero_distance():
    payload = {"content": "본문", "doc_id": "d1", "filename": "a.pdf", "chunk_index": 0}

    result = _to_dict(payload, score=1.0)

    assert result["distance"] == 0.0
    assert result["content"] == "본문"
    assert result["metadata"] == {"doc_id": "d1", "filename": "a.pdf", "chunk_index": 0}


def test_to_dict_lower_score_means_larger_distance():
    payload = {"content": "본문", "doc_id": "d1", "filename": "a.pdf", "chunk_index": 0}

    result = _to_dict(payload, score=0.25)

    assert result["distance"] == 0.75
