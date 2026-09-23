import React, { useMemo } from 'react';
import styles from './QuestionChips.module.css';

/**
 * 예시 문서(갤럭시북 사용설명서)로 답할 수 있는 질문들.
 *
 * LLM 으로 생성하지 않고 평가셋(backend-ai/evals/dataset.json)에서 가져온 뒤,
 * 9개를 실제로 물어보고 답이 나온 것만 남겼다. "배터리를 직접 교체할 수 있나요?" 는
 * 평가셋에 있는데도 실제로는 거절이 나와서 뺐다 —
 * 평가셋에 있다고 답이 나오는 게 아니다(검색 지표와 답변 품질은 따로 잰다).
 * 처음 온 사람이 누를 버튼이라, 첫인상이 "모르겠습니다" 면 그걸로 끝이다.
 */
const SAMPLE_QUESTIONS = [
  '화면을 밝게 하려면 어떤 키를 눌러야 하나요?',
  '지문을 등록하려면 어떻게 하나요?',
  '퀵 서치를 실행하는 단축키가 뭔가요?',
  'PC를 초기화하는 방법을 알려주세요',
  '시스템이 부팅되지 않을 때 복구하는 방법은 무엇인가요?',
  '배터리 캘리브레이션은 어떻게 하나요?',
];

const PICK = 3;

interface Props {
  onPick: (question: string) => void;
  disabled: boolean;
}

const QuestionChips: React.FC<Props> = ({ onPick, disabled }) => {
  // 화면이 다시 그려질 때마다 질문이 바뀌면 누르려던 걸 놓친다 — 처음 한 번만 고른다
  const picked = useMemo(() => {
    const pool = [...SAMPLE_QUESTIONS];
    const out: string[] = [];
    while (out.length < PICK && pool.length > 0) {
      out.push(...pool.splice(Math.floor(Math.random() * pool.length), 1));
    }
    return out;
  }, []);

  return (
    <div className={styles.chips}>
      <span className={styles.label}>이렇게 물어보세요</span>
      {picked.map((q) => (
        <button key={q} className={styles.chip} onClick={() => onPick(q)} disabled={disabled}>
          {q}
        </button>
      ))}
    </div>
  );
};

export default QuestionChips;
