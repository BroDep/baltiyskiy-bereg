import React from 'react';

const LABELS = { high: 'Высокая уверенность', medium: 'Средняя уверенность', low: 'Низкая уверенность' };

export default function ConfidenceBadge({ label, score }) {
  const level = label === 'high' ? 'high' : label === 'medium' ? 'medium' : 'low';
  return (
    <span className={`confidence-badge confidence-badge--${level}`}>
      {LABELS[level]} ({score}/10)
    </span>
  );
}
