// TODO: Компонент одного сообщения в чате
//
// Props:
//   role: "user" | "assistant"
//   content: string (markdown)
//   meta?: { confidence_label, confidence_score, sources, escalate }
//
// Логика:
//   - Выравнивать пузырь вправо (user) или влево (assistant)
//   - Рендерить content через react-markdown
//   - Для role="assistant" показать <ConfidenceBadge /> и <SourceList /> (если есть sources)
//   - Если meta.escalate === true — выделить сообщение особым стилем (предупреждение)
