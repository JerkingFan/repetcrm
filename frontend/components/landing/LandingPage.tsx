"use client";

import Link from "next/link";
import { useEffect, useRef, useState, type ReactNode } from "react";

function useReveal<T extends HTMLElement>(once = true) {
  const ref = useRef<T | null>(null);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      el.classList.add("is-visible");
      return;
    }
    const io = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          el.classList.add("is-visible");
          if (once) io.disconnect();
        }
      },
      { threshold: 0.12, rootMargin: "0px 0px -6% 0px" }
    );
    io.observe(el);
    return () => io.disconnect();
  }, [once]);
  return ref;
}

function Reveal({
  children,
  className = "",
  as: Tag = "div",
}: {
  children: ReactNode;
  className?: string;
  as?: "div" | "section" | "article" | "blockquote" | "li";
}) {
  const ref = useReveal<HTMLElement>();
  return (
    <Tag ref={ref as never} className={`lp-reveal ${className}`.trim()}>
      {children}
    </Tag>
  );
}

function ProductCanvas() {
  return (
    <div className="lp-canvas" aria-hidden>
      <div className="lp-canvas-ambient" />
      <div className="lp-canvas-window">
        <div className="lp-canvas-chrome">
          <div className="lp-canvas-dots">
            <i />
            <i />
            <i />
          </div>
          <div className="lp-canvas-url">app.repetcrm.ru/dashboard</div>
        </div>
        <div className="lp-canvas-app">
          <aside className="lp-canvas-rail">
            <div className="lp-canvas-mark">R</div>
            <nav>
              <span className="on">Дашборд</span>
              <span>Ученики</span>
              <span>Занятия</span>
              <span>Настройки</span>
            </nav>
          </aside>
          <div className="lp-canvas-pane">
            <header>
              <div>
                <p className="lp-canvas-eyebrow">Сегодня</p>
                <h3>Практика без хаоса</h3>
              </div>
              <div className="lp-canvas-metric">
                <em>+600 Br</em>
                <span>за месяц</span>
              </div>
            </header>
            <div className="lp-canvas-grid">
              <div className="lp-canvas-card">
                <p className="lp-canvas-eyebrow">Расписание</p>
                <ul>
                  <li>
                    <strong>Анна · алгебра</strong>
                    <span>18:00 · оплачено</span>
                  </li>
                  <li>
                    <strong>Максим · пробный</strong>
                    <span>16:30 · долг 40</span>
                  </li>
                  <li>
                    <strong>София · английский</strong>
                    <span>19:30 · пакет</span>
                  </li>
                </ul>
              </div>
              <div className="lp-canvas-card lp-canvas-card-accent">
                <p className="lp-canvas-eyebrow">AI-домашка</p>
                <h4>ДЗ для Анны К.</h4>
                <p>4 задачи · PDF готов за 28 сек</p>
                <div className="lp-canvas-bar">
                  <i />
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

const PAINS = [
  {
    title: "−10–20% дохода",
    text: "Потерянные оплаты и забытые занятия в таблицах и чатах",
  },
  {
    title: "Выгорание",
    text: "Час на каждую домашку вместо живого общения с учениками",
  },
  {
    title: "Непремиальный вид",
    text: "Скриншоты из Word вместо красивых PDF — родители замечают",
  },
  {
    title: "Страх неорганизованности",
    text: "Стыдно, когда родитель спрашивает «а сколько мы должны?»",
  },
];

const WHY = [
  {
    title: "52 репетитора доверяют нам",
    text: "Уже сократили время на организационную рутину на 40% и перестали терять деньги из-за хаоса в записях.",
  },
  {
    title: "AI-ассистент для домашек",
    text: "Подбирает персонализированные задания под темы, уровень и пробелы каждого ученика — 1 минута вместо 30.",
  },
  {
    title: "Учёт оплат на автопилоте",
    text: "Система сама напомнит, кто не заплатил, и покажет чистую прибыль за месяц.",
  },
  {
    title: "Работайте откуда угодно",
    text: "Телефон, планшет, компьютер — без установки. Старт за 2 минуты.",
  },
];

const STEPS = [
  {
    n: "01",
    title: "Чек-лист после занятия",
    text: "Провели урок → отметили темы, сложность и понимание ученика.",
  },
  {
    n: "02",
    title: "AI за 30 секунд",
    text: "Нейросеть собирает персонализированное ДЗ на ваших данных.",
  },
  {
    n: "03",
    title: "Готовый PDF",
    text: "Скачиваете файл или отправляете ученику в кабинет одной ссылкой.",
  },
];

const AUDIENCE = [
  {
    title: "Репетитор-одиночка",
    text: "5–15 учеников, всё в голове и блокноте. Перестаньте терять 10–20% дохода и выглядите профессионально перед родителями.",
  },
  {
    title: "Онлайн-преподаватель",
    text: "Zoom, Telegram, десятки чатов. Единая CRM с телефона — учёт занятий и PDF-домашки в один клик.",
  },
  {
    title: "Эксперт и премиум-сервис",
    text: "Высокий чек, высокие ожидания. Красивые персонализированные PDF подчеркнут статус и сэкономят часы подготовки.",
  },
];

const REVIEWS = [
  {
    quote:
      "Наконец-то я вижу, кто и сколько мне должен. За первый месяц вернула 400 Br пропущенных оплат.",
    name: "Марина К.",
    role: "Репетитор математики",
  },
  {
    quote:
      "Домашки, на которые уходил час, теперь делаю за минуту. Ученики в восторге, а я не выгораю.",
    name: "Алексей С.",
    role: "Онлайн-преподаватель английского",
  },
];

const FAQ = [
  {
    q: "Дорого — я же один репетитор",
    a: "Средний репетитор теряет 10–20% дохода из-за хаоса — это сотни Br в месяц. RepetCRM окупается уже в первый месяц: одна возвращённая оплата покрывает подписку. Плюс вы экономите до 10 часов в неделю на домашках.",
  },
  {
    q: "Я привык к таблицам Excel",
    a: "Excel не напомнит о долге, не сгенерирует домашку и не откроется с телефона между уроками. Мы помогаем перенести данные за 1 день — привычная логика остаётся, появляется автоматизация, которой в таблице нет.",
  },
  {
    q: "Нейросеть не учтёт индивидуальность моих учеников",
    a: "AI не заменяет вас — он усиливает вашу экспертизу. Вы заполняете чек-лист: темы, сложность, понимание, пробелы. Нейросеть строит задание на ваших данных, а вы всегда можете отредактировать результат перед отправкой.",
  },
];

export default function LandingPage() {
  const [scrolled, setScrolled] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [openFaq, setOpenFaq] = useState<number | null>(0);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 18);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => {
    document.body.style.overflow = menuOpen ? "hidden" : "";
    return () => {
      document.body.style.overflow = "";
    };
  }, [menuOpen]);

  const closeMenu = () => setMenuOpen(false);

  return (
    <div className="lp">
      <header className={`lp-nav${scrolled || menuOpen ? " is-solid" : ""}`}>
        <div className="lp-nav-inner">
          <a href="#top" className="lp-logo" onClick={closeMenu}>
            RepetCRM
          </a>
          <nav className="lp-nav-links" aria-label="Разделы">
            <a href="#why">Преимущества</a>
            <a href="#how">Как работает</a>
            <a href="#audience">Кому подойдёт</a>
            <a href="#reviews">Отзывы</a>
            <a href="#faq">FAQ</a>
          </nav>
          <div className="lp-nav-actions">
            <Link href="/login" className="lp-link">
              Войти
            </Link>
            <Link href="/register" className="lp-btn lp-btn-sm">
              Начать бесплатно
            </Link>
            <button
              type="button"
              className="lp-menu-btn"
              aria-label={menuOpen ? "Закрыть меню" : "Открыть меню"}
              aria-expanded={menuOpen}
              onClick={() => setMenuOpen((v) => !v)}
            >
              <span />
              <span />
            </button>
          </div>
        </div>
        {menuOpen && (
          <div className="lp-mobile">
            <a href="#why" onClick={closeMenu}>
              Преимущества
            </a>
            <a href="#how" onClick={closeMenu}>
              Как работает
            </a>
            <a href="#audience" onClick={closeMenu}>
              Кому подойдёт
            </a>
            <a href="#reviews" onClick={closeMenu}>
              Отзывы
            </a>
            <a href="#faq" onClick={closeMenu}>
              FAQ
            </a>
            <Link href="/register" className="lp-btn" onClick={closeMenu}>
              Начать бесплатно
            </Link>
          </div>
        )}
      </header>

      <main id="top">
        <section className="lp-hero">
          <div className="lp-hero-veil" aria-hidden />
          <div className="lp-shell lp-hero-copy">
            <p className="lp-brand lp-in lp-d1">RepetCRM</p>
            <h1 className="lp-hero-title lp-in lp-d2">Практика без хаоса</h1>
            <p className="lp-hero-sub lp-in lp-d3">
              Учёт занятий и оплат + AI-домашки за минуту — вместо Excel, чатов и выгорания.
            </p>
            <div className="lp-hero-cta lp-in lp-d4">
              <Link href="/register" className="lp-btn">
                Начать бесплатно
              </Link>
              <a href="#how" className="lp-btn lp-btn-ghost">
                Как это работает
              </a>
            </div>
            <p className="lp-hero-trust lp-in lp-d5">52 репетитора уже с нами</p>
          </div>
          <div className="lp-hero-stage lp-in lp-d6">
            <ProductCanvas />
          </div>
        </section>

        <section className="lp-section" id="pain">
          <div className="lp-shell">
            <Reveal>
              <p className="lp-kicker">Знакомо?</p>
              <h2 className="lp-h2">Вы не одиноки — хаос в организации стоит денег и энергии</h2>
            </Reveal>
            <div className="lp-pain-list">
              {PAINS.map((item, i) => (
                <Reveal key={item.title} className={`lp-pain-item lp-delay-${i}`} as="article">
                  <h3>{item.title}</h3>
                  <p>{item.text}</p>
                </Reveal>
              ))}
            </div>
          </div>
        </section>

        <section className="lp-section lp-section-alt" id="why">
          <div className="lp-shell">
            <Reveal>
              <p className="lp-kicker">Почему мы</p>
              <h2 className="lp-h2">Всё, что нужно профессиональному репетитору</h2>
            </Reveal>
            <div className="lp-feature-list">
              {WHY.map((item, i) => (
                <Reveal key={item.title} className={`lp-feature lp-delay-${i}`} as="article">
                  <h3>{item.title}</h3>
                  <p>{item.text}</p>
                </Reveal>
              ))}
            </div>
          </div>
        </section>

        <section className="lp-section lp-section-ink" id="how">
          <div className="lp-shell">
            <Reveal>
              <p className="lp-kicker on-dark">Как работает</p>
              <h2 className="lp-h2 on-dark">От занятия до готового PDF за минуту</h2>
              <p className="lp-lead on-dark">Три простых шага — без ручного труда в Word и чатах.</p>
            </Reveal>
            <ol className="lp-steps">
              {STEPS.map((s, i) => (
                <Reveal key={s.n} className={`lp-step lp-delay-${i}`} as="li">
                  <span>{s.n}</span>
                  <div>
                    <h3>{s.title}</h3>
                    <p>{s.text}</p>
                  </div>
                </Reveal>
              ))}
            </ol>
          </div>
        </section>

        <section className="lp-section" id="audience">
          <div className="lp-shell">
            <Reveal>
              <p className="lp-kicker">Кому подойдёт</p>
              <h2 className="lp-h2">Независимо от формата — онлайн или офлайн</h2>
              <p className="lp-lead">Один ученик или двадцать. Один кабинет вместо десятка чатов.</p>
            </Reveal>
            <div className="lp-audience">
              {AUDIENCE.map((item, i) => (
                <Reveal key={item.title} className={`lp-audience-item lp-delay-${i}`} as="article">
                  <h3>{item.title}</h3>
                  <p>{item.text}</p>
                </Reveal>
              ))}
            </div>
          </div>
        </section>

        <section className="lp-section lp-section-alt" id="reviews">
          <div className="lp-shell">
            <Reveal>
              <p className="lp-kicker">Отзывы</p>
              <h2 className="lp-h2">Репетиторы, которые уже навели порядок</h2>
            </Reveal>
            <div className="lp-quotes">
              {REVIEWS.map((r, i) => (
                <Reveal key={r.name} className={`lp-quote lp-delay-${i}`} as="blockquote">
                  <p>«{r.quote}»</p>
                  <footer>
                    <strong>{r.name}</strong>
                    <span>{r.role}</span>
                  </footer>
                </Reveal>
              ))}
            </div>
          </div>
        </section>

        <section className="lp-section" id="faq">
          <div className="lp-shell lp-shell-narrow">
            <Reveal>
              <p className="lp-kicker">FAQ</p>
              <h2 className="lp-h2">Частые вопросы</h2>
            </Reveal>
            <div className="lp-faq">
              {FAQ.map((item, i) => {
                const open = openFaq === i;
                return (
                  <Reveal key={item.q} className={`lp-faq-item lp-delay-${i}`}>
                    <button
                      type="button"
                      className="lp-faq-q"
                      aria-expanded={open}
                      onClick={() => setOpenFaq(open ? null : i)}
                    >
                      <span>{item.q}</span>
                      <i className={open ? "is-open" : ""} />
                    </button>
                    <div className={`lp-faq-a${open ? " is-open" : ""}`}>
                      <p>{item.a}</p>
                    </div>
                  </Reveal>
                );
              })}
            </div>
          </div>
        </section>

        <section className="lp-final">
          <div className="lp-shell">
            <Reveal>
              <h2 className="lp-h2 on-dark">Соберите практику в порядок</h2>
              <p className="lp-lead on-dark">
                Старт за 2 минуты. Без установки. На телефоне или ноутбуке.
              </p>
              <div className="lp-hero-cta">
                <Link href="/register" className="lp-btn lp-btn-light">
                  Создать кабинет
                </Link>
                <a
                  href="https://t.me/diogen52"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="lp-btn lp-btn-ghost on-dark"
                >
                  Написать в Telegram
                </a>
              </div>
            </Reveal>
          </div>
        </section>
      </main>

      <footer className="lp-footer">
        <div className="lp-shell lp-footer-grid">
          <div>
            <p className="lp-logo">RepetCRM</p>
            <p className="lp-footer-text">
              CRM для репетиторов с AI-генерацией домашних заданий. Порядок в финансах и премиальный
              сервис для учеников.
            </p>
          </div>
          <div>
            <p className="lp-footer-label">Контакты</p>
            <a href="mailto:kulbakocnt@gmail.com">kulbakocnt@gmail.com</a>
            <a href="https://t.me/diogen52" target="_blank" rel="noopener noreferrer">
              Telegram · @diogen52
            </a>
          </div>
          <div className="lp-footer-meta">
            <p>© {new Date().getFullYear()} RepetCRM</p>
            <Link href="/login">Вход в кабинет</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
