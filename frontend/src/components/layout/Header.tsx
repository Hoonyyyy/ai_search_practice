import React from 'react';
import styles from './Header.module.css';

type Tab = 'search' | 'dashboard';

interface Props {
  activeTab: Tab;
  onTabChange: (tab: Tab) => void;
}

const TABS: { key: Tab; label: string }[] = [
  { key: 'search', label: '문서 검색' },
  { key: 'dashboard', label: '성능 대시보드' },
];

const Header: React.FC<Props> = ({ activeTab, onTabChange }) => (
  <header className={styles.header}>
    <div className={styles.logo}>RAG Search</div>
    {TABS.map(({ key, label }) => (
      <button
        key={key}
        className={`${styles.tab} ${activeTab === key ? styles.tabActive : ''}`}
        onClick={() => onTabChange(key)}
      >
        {label}
      </button>
    ))}
  </header>
);

export default Header;
