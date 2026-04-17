import React, { useEffect, useRef, useState } from 'react';
import {
  Bar, BarChart, CartesianGrid, Legend,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts';
import './Analytics.css';

const TODAY = new Date().toISOString().slice(0, 10);
const LIMIT = 20;

export default function Analytics() {
  const [stats, setStats] = useState(null);
  const [hourly, setHourly] = useState([]);
  const [daily, setDaily] = useState([]);

  const [items, setItems] = useState([]);
  const [totalTickets, setTotalTickets] = useState(0);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);
  const [loadingTickets, setLoadingTickets] = useState(false);

  const [search, setSearch] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [status, setStatus] = useState('all');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');

  const sentinelRef = useRef(null);
  const hasDateFilter = !!(dateFrom || dateTo);

  function buildQS(extra = {}) {
    const p = new URLSearchParams(extra);
    if (dateFrom) p.set('date_from', dateFrom);
    if (dateTo)   p.set('date_to', dateTo);
    return p.toString();
  }

  // ── Charts + stats (reload on date change) ──────────────────────────────────
  useEffect(() => {
    const qs = buildQS();
    const q  = qs ? `?${qs}` : '';
    fetch(`/api/analytics/stats${q}`).then(r => r.json()).then(setStats).catch(() => {});
    fetch(`/api/analytics/hourly${q}`).then(r => r.json()).then(setHourly).catch(() => {});
    fetch(`/api/analytics/daily${q}`).then(r => r.json()).then(setDaily).catch(() => {});
  }, [dateFrom, dateTo]); // eslint-disable-line

  // ── Debounce search ──────────────────────────────────────────────────────────
  useEffect(() => {
    const t = setTimeout(() => setDebouncedSearch(search), 400);
    return () => clearTimeout(t);
  }, [search]);

  // ── Reset list when any filter changes ───────────────────────────────────────
  useEffect(() => {
    setItems([]);
    setPage(1);
    setHasMore(true);
  }, [debouncedSearch, status, dateFrom, dateTo]);

  // ── Load tickets (fires on page or filter change) ────────────────────────────
  useEffect(() => {
    let cancelled = false;
    setLoadingTickets(true);
    const qs = buildQS({ page, limit: LIMIT, search: debouncedSearch, status });
    fetch(`/api/analytics/tickets?${qs}`)
      .then(r => r.json())
      .then(data => {
        if (cancelled) return;
        setItems(prev => page === 1 ? data.items : [...prev, ...data.items]);
        setTotalTickets(data.total);
        setHasMore(page < data.pages);
        setLoadingTickets(false);
      })
      .catch(() => { if (!cancelled) setLoadingTickets(false); });
    return () => { cancelled = true; };
  }, [page, debouncedSearch, status, dateFrom, dateTo]); // eslint-disable-line

  // ── Infinite scroll sentinel ─────────────────────────────────────────────────
  useEffect(() => {
    const sentinel = sentinelRef.current;
    if (!sentinel || !hasMore || loadingTickets) return;
    const observer = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting) setPage(p => p + 1); },
      { threshold: 0.1 },
    );
    observer.observe(sentinel);
    return () => observer.disconnect();
  }, [hasMore, loadingTickets]);

  const resolvedPct = stats ? (100 - stats.escalation_rate).toFixed(1) : '—';
  const dailyTitle  = hasDateFilter
    ? 'Передано специалисту по дням (период)'
    : 'Передано специалисту по дням (30 дн.)';

  return (
    <div className="analytics">
      <div className="analytics__stats">
        <StatCard label="Всего заявок"          value={stats?.total ?? '—'} />
        <StatCard label="Решено"                value={stats?.resolved ?? '—'} sub={stats ? `${resolvedPct}%` : ''} />
        <StatCard label="Передано специалисту"  value={stats?.escalated ?? '—'} sub={stats ? `${stats.escalation_rate}%` : ''} warn />
        <StatCard label="Средняя уверенность"   value={stats ? `${stats.avg_confidence}/10` : '—'} />
      </div>

      <div className="analytics__datefilter">
        <span className="analytics__datefilter-label">Период:</span>
        <input type="date" className="analytics__date-input" value={dateFrom} max={dateTo || TODAY} onChange={e => setDateFrom(e.target.value)} />
        <span className="analytics__datefilter-sep">—</span>
        <input type="date" className="analytics__date-input" value={dateTo} min={dateFrom} max={TODAY} onChange={e => setDateTo(e.target.value)} />
        <button
          className={`analytics__alltime-btn${!hasDateFilter ? ' analytics__alltime-btn--active' : ''}`}
          onClick={() => { setDateFrom(''); setDateTo(''); }}
        >
          За всё время
        </button>
      </div>

      <div className="analytics__charts">
        <div className="analytics__chart-card">
          <h3 className="analytics__chart-title">Распределение по часам суток</h3>
          <ResponsiveContainer width="100%" height={190}>
            <BarChart data={hourly} margin={{ top: 4, right: 8, left: -22, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e6ecf7" />
              <XAxis dataKey="hour" tick={{ fontSize: 10, fill: '#6b7f9e' }} tickFormatter={h => `${h}:00`} interval={2} />
              <YAxis tick={{ fontSize: 10, fill: '#6b7f9e' }} />
              <Tooltip formatter={v => [v, 'Заявок']} labelFormatter={h => `${h}:00`} contentStyle={TOOLTIP_STYLE} />
              <Bar dataKey="count" fill="#213565" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="analytics__chart-card">
          <h3 className="analytics__chart-title">{dailyTitle}</h3>
          <ResponsiveContainer width="100%" height={190}>
            <BarChart data={daily} margin={{ top: 4, right: 8, left: -22, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e6ecf7" />
              <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#6b7f9e' }} tickFormatter={d => d.slice(5)} interval="preserveStartEnd" />
              <YAxis tick={{ fontSize: 10, fill: '#6b7f9e' }} />
              <Tooltip contentStyle={TOOLTIP_STYLE} />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Bar dataKey="total"     name="Всего"                fill="#c9d5ed" radius={[3, 3, 0, 0]} />
              <Bar dataKey="escalated" name="Передано специалисту" fill="#213565" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="analytics__tickets">
        <div className="analytics__tickets-header">
          <h3 className="analytics__section-title">
            Заявки {totalTickets > 0 && <span className="analytics__count">{totalTickets}</span>}
          </h3>
          <div className="analytics__filters">
            <input
              className="analytics__search"
              placeholder="Поиск по тексту..."
              value={search}
              onChange={e => setSearch(e.target.value)}
            />
            <select className="analytics__select" value={status} onChange={e => setStatus(e.target.value)}>
              <option value="all">Все статусы</option>
              <option value="resolved">Решено</option>
              <option value="escalated">Передано специалисту</option>
            </select>
          </div>
        </div>

        <div className="analytics__list">
          {items.length === 0 && !loadingTickets && (
            <div className="analytics__empty">Заявки не найдены</div>
          )}
          {items.map(t => <TicketRow key={t.id} ticket={t} />)}

          {loadingTickets && (
            <div className="analytics__loading-text">
              <span className="analytics__spinner" />
              Загрузка...
            </div>
          )}

          {!loadingTickets && hasMore && <div ref={sentinelRef} className="analytics__sentinel" />}

          {!hasMore && items.length > 0 && (
            <div className="analytics__end">Показано {items.length} из {totalTickets}</div>
          )}
        </div>
      </div>
    </div>
  );
}

const TOOLTIP_STYLE = {
  background: '#fff',
  border: '1px solid #e6ecf7',
  borderRadius: 6,
  fontSize: 12,
  color: '#213565',
};

function StatCard({ label, value, sub, warn }) {
  return (
    <div className={`stat-card${warn ? ' stat-card--warn' : ''}`}>
      <div className="stat-card__value">{value}</div>
      {sub && <div className="stat-card__sub">{sub}</div>}
      <div className="stat-card__label">{label}</div>
    </div>
  );
}

function TicketRow({ ticket }) {
  const [expanded, setExpanded] = useState(false);
  const date = new Date(ticket.created_at).toLocaleString('ru', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });
  return (
    <div className={`ticket-row${expanded ? ' ticket-row--open' : ''}`} onClick={() => setExpanded(v => !v)}>
      <div className="ticket-row__header">
        <span className={`ticket-status ticket-status--${ticket.escalated ? 'escalated' : 'resolved'}`}>
          {ticket.escalated ? 'Передано' : 'Решено'}
        </span>
        <span className="ticket-row__message">{ticket.message}</span>
        <span className="ticket-row__date">{date}</span>
        <span className={`confidence-badge confidence-badge--${ticket.confidence_label}`}>
          {ticket.confidence_score}/10
        </span>
        <span className="ticket-row__chevron">{expanded ? '▲' : '▼'}</span>
      </div>
      {expanded && <div className="ticket-row__answer">{ticket.answer}</div>}
    </div>
  );
}
