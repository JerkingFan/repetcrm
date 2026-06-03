document.addEventListener('DOMContentLoaded', () => {
  // Lucide icons
  if (typeof lucide !== 'undefined') {
    lucide.createIcons();
  }

  // Mobile menu
  const menuToggle = document.getElementById('menu-toggle');
  const mobileMenu = document.getElementById('mobile-menu');
  const iconMenu = document.getElementById('icon-menu');
  const iconClose = document.getElementById('icon-close');

  const closeMobileMenu = () => {
    mobileMenu.classList.add('hidden');
    iconMenu.classList.remove('hidden');
    iconClose.classList.add('hidden');
    menuToggle.setAttribute('aria-expanded', 'false');
    document.body.style.overflow = '';
  };

  menuToggle?.addEventListener('click', () => {
    const isOpen = !mobileMenu.classList.contains('hidden');
    if (isOpen) {
      closeMobileMenu();
    } else {
      mobileMenu.classList.remove('hidden');
      iconMenu.classList.add('hidden');
      iconClose.classList.remove('hidden');
      menuToggle.setAttribute('aria-expanded', 'true');
      document.body.style.overflow = 'hidden';
      lucide?.createIcons();
    }
  });

  document.querySelectorAll('.mobile-link').forEach((link) => {
    link.addEventListener('click', closeMobileMenu);
  });

  // Header scroll shadow
  const header = document.getElementById('header');
  const onScroll = () => {
    if (window.scrollY > 20) {
      header?.classList.add('scrolled');
    } else {
      header?.classList.remove('scrolled');
    }
  };
  window.addEventListener('scroll', onScroll, { passive: true });
  onScroll();

  // Scroll reveal (Intersection Observer)
  const revealElements = document.querySelectorAll('.reveal');
  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  if (prefersReducedMotion) {
    revealElements.forEach((el) => el.classList.add('visible'));
  } else {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add('visible');
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.12, rootMargin: '0px 0px -40px 0px' }
    );
    revealElements.forEach((el) => observer.observe(el));
  }

  // Form validation & submit
  const form = document.getElementById('lead-form');
  const validators = {
    name: (value) => {
      if (!value.trim()) return 'Укажите ваше имя';
      if (value.trim().length < 2) return 'Имя должно содержать минимум 2 символа';
      return null;
    },
    email: (value) => {
      if (!value.trim()) return 'Укажите email';
      const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (!re.test(value.trim())) return 'Введите корректный email';
      return null;
    },
    students: (value) => (!value ? 'Выберите количество учеников' : null),
    pain: (value) => (!value ? 'Выберите главную боль' : null),
    consent: (checked) => (!checked ? 'Необходимо согласие на обработку данных' : null),
  };

  const showError = (field, message) => {
    const input = document.getElementById(field);
    const errorEl = document.querySelector(`[data-for="${field}"]`);
    if (message) {
      input?.classList.add('error');
      if (errorEl) {
        errorEl.textContent = message;
        errorEl.classList.remove('hidden');
      }
    } else {
      input?.classList.remove('error');
      if (errorEl) {
        errorEl.textContent = '';
        errorEl.classList.add('hidden');
      }
    }
  };

  const validateForm = () => {
    let valid = true;
    const name = document.getElementById('name').value;
    const email = document.getElementById('email').value;
    const students = document.getElementById('students').value;
    const pain = document.getElementById('pain').value;
    const consent = document.getElementById('consent').checked;

    const fields = [
      ['name', validators.name(name)],
      ['email', validators.email(email)],
      ['students', validators.students(students)],
      ['pain', validators.pain(pain)],
      ['consent', validators.consent(consent)],
    ];

    fields.forEach(([field, error]) => {
      showError(field, error);
      if (error) valid = false;
    });

    return valid;
  };

  ['name', 'email', 'students', 'pain'].forEach((id) => {
    document.getElementById(id)?.addEventListener('input', () => {
      const el = document.getElementById(id);
      const error = validators[id](el.value);
      showError(id, error);
    });
    document.getElementById(id)?.addEventListener('blur', () => {
      const el = document.getElementById(id);
      const error = validators[id](el.value);
      if (error) showError(id, error);
    });
  });

  document.getElementById('consent')?.addEventListener('change', (e) => {
    showError('consent', validators.consent(e.target.checked));
  });

  form?.addEventListener('submit', (e) => {
    e.preventDefault();
    if (!validateForm()) return;

    const name = document.getElementById('name').value.trim();
    alert(
      `Спасибо, ${name}!\n\n` +
        'Мы отправили мини-книгу «7 критических ошибок репетитора» на ваш email и подготовим персональный расчёт экономии.\n\n' +
        'Проверьте почту в течение 5 минут (не забудьте папку «Спам»).'
    );
    form.reset();
    document.querySelectorAll('.error-msg').forEach((el) => {
      el.textContent = '';
      el.classList.add('hidden');
    });
    document.querySelectorAll('.error').forEach((el) => el.classList.remove('error'));
  });
});
