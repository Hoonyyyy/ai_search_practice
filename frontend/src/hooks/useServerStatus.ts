import { useEffect, useState } from 'react';
import { pingServer } from '../api/server';

export type ServerStatus = 'checking' | 'waking' | 'ready' | 'failed';

const SHOW_WAKING_AFTER_MS = 3000;     // 이보다 빨리 답하면 배너를 띄우지 않는다 (깜빡임 방지)
const RETRY_MS = 5000;                 // 실패하면 5초 뒤 다시 묻는다
const GIVE_UP_MS = 4 * 60 * 1000;      // 4분이 지나도 안 깨면 포기 (실측 최악 2분 30초)

export function useServerStatus() {
  const [status, setStatus] = useState<ServerStatus>('checking');
  const [elapsedSec, setElapsedSec] = useState(0);

  useEffect(() => {
    const started = Date.now();
    let stopped = false;

    // 1초마다 경과 시간을 올리고, 3초가 지나면 '깨우는 중' 으로 바꾼다
    const tick = setInterval(() => {
      const ms = Date.now() - started;
      setElapsedSec(Math.floor(ms / 1000));
      if (ms >= SHOW_WAKING_AFTER_MS) {
        setStatus((s) => (s === 'checking' ? 'waking' : s));
      }
    }, 1000);

    // 답할 때까지 묻는다
    const waitUntilReady = async () => {
      while (!stopped) {
        if (await pingServer()) {
          if (!stopped) setStatus('ready');
          break;
        }
        if (Date.now() - started > GIVE_UP_MS) {
          if (!stopped) setStatus('failed');
          break;
        }
        await new Promise((resolve) => setTimeout(resolve, RETRY_MS));
      }
      clearInterval(tick);
    };
    waitUntilReady();

    // 화면에서 사라질 때 정리
    return () => {
      stopped = true;
      clearInterval(tick);
    };
  }, []);

  return { status, elapsedSec };
}
