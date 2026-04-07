import React from 'react';
import styles from './StatCard.module.css';

interface Props {
  label: string;
  value: string | number;
  color: string;
  sub?: string;
}

const StatCard: React.FC<Props> = ({ label, value, color, sub }) => (
  <div className={styles.card}>
    <div className={styles.label}>{label}</div>
    <div className={styles.value} style={{ color }}>{value}</div>
    {sub && <div className={styles.sub}>{sub}</div>}
  </div>
);

export default StatCard;
