function formatSourceLabel(source) {
  if (source.ticket_id) {
    return `Тикет #${source.ticket_id}`;
  }
  if (source.kb_doc_id) {
    return `KB #${source.kb_doc_id}`;
  }
  return "Источник";
}

function SourceList({ sources }) {
  return (
    <details className="sources-list">
      <summary>Источники ({sources.length})</summary>
      <ul>
        {sources.map((source, index) => (
          <li className="sources-item" key={`${source.title}-${index}`}>
            <strong>{formatSourceLabel(source)}</strong>
            <div>{source.title}</div>
            <small>Релевантность: {Number(source.score).toFixed(2)}</small>
            <small>{source.excerpt}</small>
          </li>
        ))}
      </ul>
    </details>
  );
}

export default SourceList;
