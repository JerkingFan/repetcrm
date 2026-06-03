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

});
