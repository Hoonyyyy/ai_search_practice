import React from 'react';
import { ServerStatus } from '../../hooks/useServerStatus';
import styles from './ServerStatusBanner.module.css';

interface Props {
  status: ServerStatus;
  elapsedSec: number;
}

const formatElapsed = (sec: number) =>
  sec < 60 ? `${sec}초` : `${Math.floor(sec / 60)}분 ${sec % 60}초`;

const ServerStatusBanner: React.FC<Props> = ({ status, elapsedSec }) => {
  if (status === 'waking') {
    return (
      <div className={styles.banner} role="status">
        <strong>⏳ 서버를 깨우는 중이에요 · {formatElapsed(elapsedSec)} 경과</strong>
        <span className={styles.sub}>
          무료 서버라 한동안 쓰지 않으면 잠들어요. 보통 1~2분 걸리고, 깨어나면 화면이 저절로 채워져요.
        </span>
      </div>
    );
  }

  if (status === 'failed') {
    return (
      <div className={`${styles.banner} ${styles.failed}`} role="alert">
        <strong>서버에 연결하지 못했어요.</strong>
        <button className={styles.retryBtn} onClick={() => window.location.reload()}>
          다시 시도
        </button>
      </div>
    );
  }

  return null;
};

export default ServerStatusBanner;
