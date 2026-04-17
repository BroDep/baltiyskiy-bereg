// TODO: Корневой компонент приложения
//
// State:
//   messages: [{ role: "user"|"assistant", content, meta? }]
//   sessionId: string (генерировать uuid при монтировании, хранить в sessionStorage)
//   isLoading: boolean
//
// Логика:
//   - sendMessage(text): POST /api/chat → добавить ответ в messages
//   - При загрузке запросить GET /api/health и показать статус в шапке
//
// Верстка:
//   <Header />        — название, статус системы
//   <ChatWindow />    — список сообщений
//   <MessageInput />  — поле ввода + кнопка отправки
