import React from 'react';

export default function SourceList({ sources }) {
  if (!sources?.length) return null;

  return (
    <details className="source-list">
      <summary>Источники ({sources.length})</summary>
      <div className="source-list__items">
        {sources.map((src, i) => {
          const isTicket = src.ticket_id != null;
          const id = isTicket ? src.ticket_id : src.kb_doc_id;
          return (
            <div key={i} className="source-item">
              <div className="source-item__header">
                <span className={`source-badge source-badge--${isTicket ? 'ticket' : 'kb'}`}>
                  {isTicket ? `Тикет #${id}` : `KB #${id}`}
                </span>
                <span className="source-item__title">{src.title}</span>
                <span className="source-item__score">{src.score.toFixed(2)}</span>
              </div>
              {src.excerpt && <div className="source-item__excerpt">{src.excerpt}</div>}
            </div>
          );
        })}
      </div>
    </details>
  );
}
