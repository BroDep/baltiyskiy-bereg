import React from 'react';
import ReactMarkdown from 'react-markdown';
import ConfidenceBadge from './ConfidenceBadge';
import SourceList from './SourceList';

export default function Message({ role, content, meta }) {
  const isAssistant = role === 'assistant';
  const escalate = meta?.escalate;

  return (
    <div className={`message message--${role}`}>
      <div className={`message__bubble${escalate ? ' message__bubble--escalate' : ''}`}>
        {escalate && (
          <div className="escalate-banner">
            <span>⚠</span>
            <span>Запрос передан специалисту</span>
          </div>
        )}
        <ReactMarkdown>{content}</ReactMarkdown>
      </div>
      {isAssistant && meta && (
        <div className="message__meta">
          <ConfidenceBadge label={meta.confidence_label} score={meta.confidence_score} />
          {meta.sources?.length > 0 && <SourceList sources={meta.sources} />}
        </div>
      )}
    </div>
  );
}
