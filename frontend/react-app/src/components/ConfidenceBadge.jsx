function ConfidenceBadge({ label, score }) {
  const labels = {
    high: `Высокая уверенность (${score}/10)`,
    medium: `Средняя уверенность (${score}/10)`,
    low: `Низкая уверенность (${score}/10)`,
  };

  return (
    <span className={`confidence-badge confidence-badge--${label}`}>
      {labels[label] || `Уверенность (${score}/10)`}
    </span>
  );
}

export default ConfidenceBadge;
