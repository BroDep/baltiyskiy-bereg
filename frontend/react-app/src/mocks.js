// ── Mock data ─────────────────────────────────────────────────────────────────

const STUB_CHAT = [
  {
    keywords: ['vpn', 'удаленн', 'подключ', 'remote'],
    answer: 'Для подключения VPN выполните следующие шаги:\n\n1. Установите клиент **UniVPN** с корпоративного портала `portal.company.ru`\n2. Введите адрес сервера: `vpn.company.ru`\n3. Авторизуйтесь с доменными учётными данными\n\nЕсли соединение не устанавливается — проверьте настройки брандмауэра.',
    confidence_score: 8.5, confidence_label: 'high', escalate: false,
    sources: [
      { title: 'Тикет #23451: Настройка VPN-подключения', excerpt: 'Пользователю предложено установить UniVPN и подключиться к vpn.company.ru.', score: 0.94, ticket_id: 23451, kb_doc_id: null },
      { title: 'KB #87: Инструкция по настройке VPN', excerpt: 'Пошаговая инструкция. Поддерживаемые ОС: Windows 10/11, macOS 12+.', score: 0.88, ticket_id: null, kb_doc_id: 87 },
    ],
  },
  {
    keywords: ['пароль', 'забыл', 'сброс', 'войти', 'учётн', 'учетн'],
    answer: 'Для сброса пароля:\n\n**Самостоятельно:** `password.company.ru` → подтвердите через корп. почту\n\n**Через поддержку:** `+7 (812) 000-00-01` (доб. 101)',
    confidence_score: 9.0, confidence_label: 'high', escalate: false,
    sources: [{ title: 'KB #12: Сброс пароля учётной записи', excerpt: 'Инструкция по самостоятельному сбросу пароля.', score: 0.97, ticket_id: null, kb_doc_id: 12 }],
  },
  {
    keywords: ['принтер', 'печать', 'сканер'],
    answer: 'Для устранения проблем с принтером:\n\n1. Очистите очередь: `Устройства и принтеры → ПКМ → Просмотр очереди → Очистить`\n2. Переустановите драйвер с `drivers.company.ru`',
    confidence_score: 7.2, confidence_label: 'medium', escalate: false,
    sources: [{ title: 'Тикет #18934: Принтер HP LaserJet не печатает', excerpt: 'Решено переустановкой драйвера.', score: 0.79, ticket_id: 18934, kb_doc_id: null }],
  },
  {
    keywords: ['1с', '1c', 'бухгалтер'],
    answer: 'По вопросам 1С:\n\n- **Не запускается:** `services.msc → 1C:Enterprise → Перезапуск`\n- **Ошибка соединения:** проверьте `1c-srv.company.ru:1541`',
    confidence_score: 6.5, confidence_label: 'medium', escalate: false,
    sources: [{ title: 'KB #34: Часто задаваемые вопросы по 1С', excerpt: 'Типичные проблемы и решения.', score: 0.83, ticket_id: null, kb_doc_id: 34 }],
  },
];

const ESCALATION = {
  answer: 'К сожалению, не удалось найти подходящее решение в базе знаний.\n\nВаш запрос передан специалисту. Ожидайте ответа в течение **1 рабочего дня**.\n\nДля срочных вопросов: `+7 (812) 000-00-01`',
  confidence_score: 3.0, confidence_label: 'low', escalate: true, sources: [],
};

// ── Analytics mock data ───────────────────────────────────────────────────────

function filterByDate(tickets, dateFrom, dateTo) {
  return tickets.filter(t => {
    const d = t.created_at.slice(0, 10);
    if (dateFrom && d < dateFrom) return false;
    if (dateTo && d > dateTo) return false;
    return true;
  });
}

function computeStats(tickets) {
  const total = tickets.length;
  const escalated = tickets.filter(t => t.escalated).length;
  const avg = total ? tickets.reduce((s, t) => s + t.confidence_score, 0) / total : 0;
  return {
    total, resolved: total - escalated, escalated,
    escalation_rate: total ? +(escalated / total * 100).toFixed(1) : 0,
    avg_confidence: +avg.toFixed(1),
  };
}

function computeHourly(tickets) {
  const counts = {};
  tickets.forEach(t => {
    const h = new Date(t.created_at).getHours();
    counts[h] = (counts[h] || 0) + 1;
  });
  return Array.from({ length: 24 }, (_, h) => ({ hour: h, count: counts[h] || 0 }));
}

function computeDaily(tickets, dateFrom, dateTo) {
  const byDate = {};
  tickets.forEach(t => {
    const d = t.created_at.slice(0, 10);
    if (!byDate[d]) byDate[d] = { total: 0, escalated: 0 };
    byDate[d].total++;
    if (t.escalated) byDate[d].escalated++;
  });
  // default: last 30 days if no filter
  let keys = Object.keys(byDate).sort();
  if (!dateFrom && !dateTo) {
    const cutoff = new Date();
    cutoff.setDate(cutoff.getDate() - 30);
    const since = cutoff.toISOString().slice(0, 10);
    keys = keys.filter(k => k >= since);
  }
  return keys.map(date => ({ date, ...byDate[date] }));
}

const MESSAGES_POOL = [
  'Не работает VPN, не могу подключиться к корпоративной сети',
  'После обновления Windows VPN перестал работать',
  'Забыл пароль от Windows, как сбросить?',
  'Заблокировалась учётная запись в Active Directory',
  'Принтер не печатает, документ завис в очереди',
  'Нет доступа к сетевой папке \\\\fileserver\\shared',
  '1С не запускается, ошибка при старте',
  'Не открывается Excel, вылетает при запуске',
  'Teams не показывает статус онлайн у коллег',
  'Нет доступа к базе 1С после смены пароля',
  'Нужно установить Microsoft Office на новый компьютер',
  'Интернет очень медленный, что-то случилось с сетью?',
  'Монитор показывает чёрный экран при включении',
  'Не сканируется документ, ошибка подключения к сканеру',
  'Outlook не синхронизирует почту',
  'Не могу войти на корпоративный портал',
  'Нужен доступ к системе SAP для нового сотрудника',
  'Обновление Office завершилось с ошибкой 0x80070005',
  'Компьютер не включается, нет реакции при нажатии кнопки',
  'Клавиатура не реагирует на нажатия',
];

const ANSWERS_POOL = [
  'Установите UniVPN с portal.company.ru, сервер vpn.company.ru, логин доменный.',
  'Сбросьте пароль через password.company.ru, подтвердите через корп. почту.',
  'Очистите очередь печати, переустановите драйвер с drivers.company.ru.',
  'Перезапустите службу 1C:Enterprise через services.msc.',
  'Office переустановлен с корпоративного портала, проблема решена.',
  'Заявка передана ответственному за систему, ожидайте решения.',
  'Специалист выедет для диагностики оборудования.',
  'Доступ к сетевой папке предоставлен.',
  'Ошибка Teams устранена сбросом кэша приложения.',
  'Запрос передан специалисту технической поддержки. Ожидайте ответа.',
];

function randomDate() {
  const d = new Date();
  d.setDate(d.getDate() - Math.floor(Math.random() * 90));
  d.setHours(7 + Math.floor(Math.random() * 14));
  d.setMinutes(Math.floor(Math.random() * 60));
  return d.toISOString();
}

const ALL_TICKETS = Array.from({ length: 1000 }, (_, i) => {
  const escalated = Math.random() < 0.29;
  const score = escalated ? +(Math.random() * 3 + 1).toFixed(1) : +(Math.random() * 3 + 6.5).toFixed(1);
  return {
    id: i + 1,
    session_id: `mock-${i + 1}`,
    message: MESSAGES_POOL[i % MESSAGES_POOL.length],
    answer: escalated ? ANSWERS_POOL[9] : ANSWERS_POOL[i % 9],
    confidence_score: Math.min(10, score),
    confidence_label: score >= 8 ? 'high' : score >= 5 ? 'medium' : 'low',
    escalated,
    created_at: randomDate(),
  };
}).sort((a, b) => b.created_at.localeCompare(a.created_at));


// ── Mock history ─────────────────────────────────────────────────────────────

const HISTORY_TOPICS = [
  { q: 'Не работает VPN после обновления ноутбука', a: 'Обновите клиент UniVPN до актуальной версии с portal.company.ru.' },
  { q: 'Забыл пароль от корпоративной почты', a: 'Сбросьте пароль через password.company.ru, подтверждение через SMS.' },
  { q: 'Принтер HP не печатает на 3 этаже', a: 'Очередь очищена, драйвер переустановлен. Принтер работает.' },
  { q: 'Нет доступа к сетевой папке после отпуска', a: 'Доступ восстановлен, учётная запись была заблокирована по истечении срока.' },
  { q: '1С выдаёт ошибку при открытии базы', a: 'Перезапустите службу 1C:Enterprise через services.msc.' },
  { q: 'Teams не открывается после обновления', a: 'Сброс кэша Teams решил проблему: %AppData%\\Microsoft\\Teams.' },
  { q: 'Нужен доступ к Bitrix для нового сотрудника', a: 'Доступ предоставлен, учётная запись создана.' },
  { q: 'Монитор мигает при подключении к докстанции', a: 'Замените кабель DisplayPort, проблема решена.' },
];

let _historyIdCounter = 9000;
const MOCK_HISTORY = HISTORY_TOPICS.map((t, i) => {
  const base = new Date();
  base.setDate(base.getDate() - (HISTORY_TOPICS.length - i));
  base.setHours(9 + i);
  return [
    { id: _historyIdCounter++, role: 'user',      content: t.q, meta: null, created_at: new Date(base).toISOString() },
    { id: _historyIdCounter++, role: 'assistant', content: t.a, meta: { confidence_label: 'high', confidence_score: 8.0 + (i % 3) * 0.5, sources: [], escalate: false }, created_at: new Date(base.setMinutes(base.getMinutes() + 1)).toISOString() },
  ];
}).flat();

// ── Fetch patch ───────────────────────────────────────────────────────────────

const _fetch = window.fetch.bind(window);

window.fetch = async (url, options = {}) => {
  const urlStr = typeof url === 'string' ? url : url.toString();

  if (urlStr === '/api/auth/login' && options.method === 'POST') {
    await delay(300);
    const { username } = JSON.parse(options.body || '{}');
    return json({ user_id: 1, username: username || 'demo' });
  }

  if (urlStr.startsWith('/api/chat/history')) {
    await delay(250);
    const params = new URL(urlStr, 'http://localhost').searchParams;
    const beforeId = parseInt(params.get('before_id') || '0');
    const limit    = parseInt(params.get('limit')     || '20');
    const pool = beforeId ? MOCK_HISTORY.filter(m => m.id < beforeId) : MOCK_HISTORY;
    const slice = pool.slice(-limit);
    return json({ items: slice, has_more: pool.length > limit });
  }

  if (urlStr === '/api/health') {
    await delay(150);
    return json({ status: 'ok', db_connected: true, vector_store_connected: true });
  }

  if (urlStr === '/api/chat' && options.method === 'POST') {
    await delay(800 + Math.random() * 600);
    const { message = '' } = JSON.parse(options.body || '{}');
    const lower = message.toLowerCase();
    const stub = STUB_CHAT.find(s => s.keywords.some(k => lower.includes(k))) ?? ESCALATION;
    return json({ ...stub, session_id: 'mock-session' });
  }

  if (urlStr.startsWith('/api/analytics/')) {
    await delay(100 + Math.random() * 150);
    const params = new URL(urlStr, 'http://localhost').searchParams;
    const dateFrom = params.get('date_from') || '';
    const dateTo   = params.get('date_to')   || '';
    const filtered = filterByDate(ALL_TICKETS, dateFrom, dateTo);

    if (urlStr.includes('/stats'))  return json(computeStats(filtered));
    if (urlStr.includes('/hourly')) return json(computeHourly(filtered));
    if (urlStr.includes('/daily'))  return json(computeDaily(filtered, dateFrom, dateTo));

    if (urlStr.includes('/tickets')) {
      const page   = parseInt(params.get('page')  || '1');
      const limit  = parseInt(params.get('limit') || '20');
      const search = (params.get('search') || '').toLowerCase();
      const status = params.get('status') || 'all';

      let items = filtered;
      if (search) items = items.filter(t => t.message.toLowerCase().includes(search));
      if (status === 'resolved')  items = items.filter(t => !t.escalated);
      if (status === 'escalated') items = items.filter(t => t.escalated);

      const total = items.length;
      const pages = Math.max(1, Math.ceil(total / limit));
      return json({ total, page, pages, items: items.slice((page - 1) * limit, page * limit) });
    }
  }

  return _fetch(url, options);
};

function delay(ms) { return new Promise(r => setTimeout(r, ms)); }
function json(data) {
  return new Response(JSON.stringify(data), { status: 200, headers: { 'Content-Type': 'application/json' } });
}
