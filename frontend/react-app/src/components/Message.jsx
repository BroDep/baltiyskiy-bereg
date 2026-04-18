import ReactMarkdown from "react-markdown";

import ConfidenceBadge from "./ConfidenceBadge";
import SourceList from "./SourceList";

function Message({ role, content, meta }) {
  const hasWarning = Boolean(meta?.escalate);

  return (
    <div className={`message-row message-row--${role}`}>
      <article
        className={[
          "message-bubble",
          `message-bubble--${role}`,
          hasWarning ? "message-bubble--warning" : "",
        ]
          .filter(Boolean)
          .join(" ")}
      >
        <div className="message-markdown">
          <ReactMarkdown>{content}</ReactMarkdown>
        </div>

        {role === "assistant" && meta ? (
          <div className="message-meta">
            {meta.confidence_label ? (
              <ConfidenceBadge
                label={meta.confidence_label}
                score={meta.confidence_score}
              />
            ) : null}
            {meta.reason ? <small>{meta.reason}</small> : null}
            {meta.sources?.length ? <SourceList sources={meta.sources} /> : null}
          </div>
        ) : null}
      </article>
    </div>
  );
}

export default Message;
