// TODO: Контейнер истории диалога
//
// Props:
//   messages: Array<{ role, content, meta? }>
//   isLoading: boolean
//
// Логика:
//   - Рендерить список <Message /> для каждого сообщения
//   - При isLoading показать анимированный «…» (typing indicator) от имени ассистента
//   - Автоматически скроллить вниз при добавлении нового сообщения (useEffect + ref)
