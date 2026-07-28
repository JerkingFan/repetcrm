"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";

function useReveal<T extends HTMLElement>() {
  const ref = useRef<T | null>(null);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduced) {
      el.classList.add("is-visible");
      return;
    }
    const io = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          el.classList.add("is-visible");
          io.disconnect();
        }
      },
      { threshold: 0.18, rootMargin: "0px 0px -8% 0px" }
    );
    io.observe(el);
    return () => io.disconnect();
  }, []);
  return ref;
}

function ProductStage() {
  return (
    <div className="landing-stage" aria-hidden>
      <div className="landing-stage-glow" />
      <div className="landing-stage-frame">
        <div className="landing-stage-bar">
          <span />
          <span />
          <span />
          <p>Расписание · сегодня</p>
        </div>
        <div className="landing-stage-body">
          <aside className="landing-stage-side">
            <div className="landing-stage-side-brand">RC</div>
            <div className="landing-stage-nav" />
            <div className="landing-stage-nav" />
            <div className="landing-stage-nav on" />
            <div className="landing-stage-nav" />
          </aside>
          <div className="landing-stage-main">
            <div className="landing-stage-row">
              <div>
                <p className="landing-stage-kicker">Вт · 18:00</p>
                <p className="landing-stage-title">Анна · алгебра</p>
              </div>
              <span className="landing-stage-chip">оплачено</span>
            </div>
            <div className="landing-stage-row dim">
              <div>
                <p className="landing-stage-kicker">Ср · 16:30</p>
                <p className="landing-stage-title">Максим · пробный</p>
              </div>
              <span className="landing-stage-chip warn">долг 40</span>
            </div>
            <div className="landing-stage-hw">
              <p className="landing-stage-kicker">Домашка</p>
              <p className="landing-stage-title">PDF · 4 задачи · 28 сек</p>
              <div className="landing-stage-progress">
                <i />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function LandingPage() {
  const [scrolled, setScrolled] = useState(false);
  const pain = useReveal<HTMLElement>();
  const how = useReveal<HTMLElement>();
  const product = useReveal<HTMLElement>();
  const quote = useReveal<HTMLElement>();
  const cta = useReveal<HTMLElement>();

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 24);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <div className="landing">
      <header className={`landing-nav${scrolled ? " is-scrolled" : ""}`}>
        <div className="landing-nav-inner">
          <a href="#top" className="landing-nav-brand">
            RepetCRM
          </a>
          <div className="landing-nav-actions">
            <Link href="/login" className="landing-nav-ghost">
              Войти
            </Link>
            <Link href="/register" className="landing-nav-cta">
              Начать
            </Link>
          </div>
        </div>
      </header>

      <main id="top">
        <section className="landing-hero">
          <div className="landing-hero-mesh" aria-hidden />
          <div className="landing-hero-inner">
            <div className="landing-hero-copy">
              <p className="landing-hero-brand landing-anim-1">RepetCRM</p>
              <h1 className="landing-hero-title landing-anim-2">Практика без хаоса</h1>
              <p className="landing-hero-sub landing-anim-3">
                Занятия, оплаты и персональные домашки с AI — в одном спокойном кабинете.
              </p>
              <div className="landing-hero-cta landing-anim-4">
                <Link href="/register" className="landing-btn-primary">
                  Начать бесплатно
                </Link>
                <Link href="/login" className="landing-btn-ghost">
                  Уже есть аккаунт
                </Link>
              </div>
            </div>
            <div className="landing-hero-visual landing-anim-5">
              <ProductStage />
            </div>
          </div>
        </section>

        <section ref={pain} className="landing-section landing-reveal">
          <div className="landing-section-inner landing-pain">
            <h2 className="landing-h2">Знакомо?</h2>
            <p className="landing-lead">
              Оплаты в чатах. Домашки в Word. Расписание в голове. Родитель спрашивает «сколько должны?» — и становится стыдно.
            </p>
            <p className="landing-lead-strong">
              RepetCRM возвращает деньги, время и ощущение, что вы ведёте практику, а не таблицу.
            </p>
          </div>
        </section>

        <section id="how" ref={how} className="landing-section landing-section-ink landing-reveal">
          <div className="landing-section-inner">
            <h2 className="landing-h2 on-ink">Три шага после урока</h2>
            <ol className="landing-steps">
              <li>
                <span>01</span>
                <div>
                  <h3>Чек-лист</h3>
                  <p>Темы, сложность, понимание — за минуту после занятия.</p>
                </div>
              </li>
              <li>
                <span>02</span>
                <div>
                  <h3>AI-домашка</h3>
                  <p>Персональный PDF под ученика, а не шаблон из интернета.</p>
                </div>
              </li>
              <li>
                <span>03</span>
                <div>
                  <h3>Кабинет</h3>
                  <p>Ученик сдаёт, вы видите долги и прогресс без переписок.</p>
                </div>
              </li>
            </ol>
          </div>
        </section>

        <section ref={product} className="landing-section landing-reveal">
          <div className="landing-section-inner landing-product">
            <h2 className="landing-h2">Один кабинет вместо десяти чатов</h2>
            <p className="landing-lead">
              Расписание, пробные, баланс, портал ученика и напоминания родителям — без Excel и скриншотов.
            </p>
            <div className="landing-product-grid">
              <article>
                <h3>Учёт денег</h3>
                <p>Кто должен, кто оплатил, пакеты уроков — на одном экране.</p>
              </article>
              <article>
                <h3>AI-домашки</h3>
                <p>Из чек-листа в красивый PDF за десятки секунд.</p>
              </article>
              <article>
                <h3>Кабинет ученика</h3>
                <p>Ссылка ученику: расписание, сдача ДЗ, фокус-режим.</p>
              </article>
            </div>
          </div>
        </section>

        <section ref={quote} className="landing-section landing-quote landing-reveal">
          <div className="landing-section-inner">
            <blockquote>
              <p>
                «Наконец-то я вижу, кто и сколько мне должен. За первый месяц вернула 400&nbsp;Br
                пропущенных оплат.»
              </p>
              <footer>Марина · репетитор математики</footer>
            </blockquote>
          </div>
        </section>

        <section ref={cta} className="landing-section landing-final landing-reveal">
          <div className="landing-section-inner landing-final-inner">
            <h2 className="landing-h2">Соберите практику в порядок</h2>
            <p className="landing-lead">Старт за пару минут. Без установки. С телефона или ноутбука.</p>
            <div className="landing-hero-cta">
              <Link href="/register" className="landing-btn-primary">
                Создать кабинет
              </Link>
              <a href="https://t.me/diogen52" target="_blank" rel="noopener noreferrer" className="landing-btn-ghost">
                Написать в Telegram
              </a>
            </div>
          </div>
        </section>
      </main>

      <footer className="landing-footer">
        <div className="landing-footer-inner">
          <p className="landing-footer-brand">RepetCRM</p>
          <div className="landing-footer-links">
            <a href="mailto:kulbakocnt@gmail.com">kulbakocnt@gmail.com</a>
            <a href="https://t.me/diogen52" target="_blank" rel="noopener noreferrer">
              @diogen52
            </a>
            <Link href="/login">Вход</Link>
          </div>
          <p className="landing-footer-copy">© {new Date().getFullYear()} RepetCRM</p>
        </div>
      </footer>
    </div>
  );
}
