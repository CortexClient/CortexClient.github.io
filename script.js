/* Static release UI: no network dependencies or script execution. */
(() => {
  'use strict';
  const config = window.SITE_CONFIG || {};
  const $ = selector => document.querySelector(selector);
  const $$ = selector => [...document.querySelectorAll(selector)];
  const field = (name, value) => $$(`[data-field="${name}"]`).forEach(el => { el.textContent = value; });
  function https(value) {
    try {
      const url = new URL(value);
      return url.protocol === 'https:' && !url.username && !url.password ? url.href : null;
    } catch { return null; }
  }
  const downloadUrl = https(config.downloadUrl);
  const releaseUrl = https(config.releaseUrl);
  const rawSiteUrl = https(config.siteUrl);
  const siteUrl = rawSiteUrl && !new URL(rawSiteUrl).search && !new URL(rawSiteUrl).hash
    ? rawSiteUrl.replace(/\/+$/, '') + '/' : null;
  const validHash = /^[a-f0-9]{64}$/i.test(config.sha256 || '');
  field('version', config.version || 'В описании релиза');
  field('platform', config.platform || 'В описании релиза');
  field('fileName', config.fileName || 'Ожидает публикации');
  field('fileSize', config.fileSize || 'Пока не указан');
  field('sha256', validHash ? config.sha256 : 'Будет опубликован со сборкой');
  field('downloadStatus', downloadUrl ? 'Сборка доступна для загрузки' : 'Готовим ссылку на сборку');
  field('releaseHost', releaseUrl ? new URL(releaseUrl).hostname : 'Будет указан с релизом');

  const dialog = $('#download-dialog');
  $$('[data-download]').forEach(link => {
    link.removeAttribute('aria-disabled');
    if (downloadUrl) {
      link.href = downloadUrl;
      link.setAttribute('aria-label', `Скачать ${config.product || 'сборку'}`);
      if (config.fileName) link.setAttribute('download', config.fileName);
    } else if (dialog) {
      link.setAttribute('aria-haspopup', 'dialog');
      link.addEventListener('click', event => {
        event.preventDefault();
        clearEffects();
        if (!dialog.open) dialog.showModal();
      });
    }
  });
  $$('[data-release]').forEach(link => {
    link.hidden = !releaseUrl;
    if (releaseUrl) {
      link.href = releaseUrl;
      link.rel = 'noopener noreferrer';
    }
  });
  $('.dialog-close')?.addEventListener('click', () => dialog?.close());
  dialog?.addEventListener('click', event => {
    const rect = dialog.getBoundingClientRect();
    if (event.target === dialog && (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom)) dialog.close();
  });

  const menu = $('.menu-toggle');
  const nav = $('#site-nav');
  function toggleMenu(open, restoreFocus = false) {
    if (!menu || !nav) return;
    nav.classList.toggle('is-open', open);
    menu.setAttribute('aria-expanded', String(open));
    menu.setAttribute('aria-label', open ? 'Закрыть меню' : 'Открыть меню');
    if (restoreFocus) menu.focus();
  }
  menu?.addEventListener('click', () => toggleMenu(menu.getAttribute('aria-expanded') !== 'true'));
  nav?.addEventListener('click', event => { if (event.target.closest('a')) toggleMenu(false); });
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && menu?.getAttribute('aria-expanded') === 'true') toggleMenu(false, true);
  });
  document.addEventListener('click', event => {
    if (!event.target.closest('.site-header')) toggleMenu(false);
  });
  matchMedia('(min-width: 901px)').addEventListener('change', event => { if (event.matches) toggleMenu(false); });

  let toastTimer;
  function notify(message) {
    const toast = $('#toast');
    if (!toast) return;
    toast.textContent = message;
    toast.hidden = false;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => { toast.hidden = true; }, 3200);
  }
  async function copy(value, message) {
    try { await navigator.clipboard.writeText(value); notify(message); }
    catch { notify('Выделите текст и скопируйте его вручную.'); }
  }
  const copyHash = $('[data-copy-hash]');
  if (copyHash) {
    copyHash.hidden = !validHash;
    copyHash.addEventListener('click', () => copy(config.sha256, 'SHA-256 скопирован'));
  }
  $('[data-copy-code]')?.addEventListener('click', () => {
    const code = $('#code-sample');
    if (code) copy(code.textContent, 'Пример Java скопирован');
  });
  const samples = {
    hello: '// Класс — точка входа\npublic class Main {\n    public static void main(String[] args) {\n        System.out.println("Hello, Minecraft!");\n    }\n}',
    table: '// Массив перечисляет моды\nString[] mods = {"Optimization", "UI", "Skins"};\nfor (String mod : mods) {\n    System.out.println(mod);\n}',
    function: '// Функция считает средний FPS\nstatic int fps(int frames, int seconds) {\n    return frames / seconds;\n}\nSystem.out.println(fps(240, 4))'
  };
  $$('[data-sample]').forEach(button => button.addEventListener('click', () => {
    if (!samples[button.dataset.sample] || !$('#code-sample')) return;
    $('#code-sample').textContent = samples[button.dataset.sample];
    $$('[data-sample]').forEach(tab => tab.setAttribute('aria-pressed', String(tab === button)));
  }));
  $$('[data-detail]').forEach(button => button.addEventListener('click', () => {
    $$('[data-detail]').forEach(tab => tab.setAttribute('aria-pressed', String(tab === button)));
    $$('[data-panel]').forEach(panel => { panel.hidden = panel.dataset.panel !== button.dataset.detail; });
  }));

  // Effects use a fixed number of nodes, stop when idle, and follow system motion preferences.
  const effectsMedia = matchMedia('(hover: hover) and (pointer: fine) and (prefers-reduced-motion: no-preference)');
  let layer = null, aura = null, particles = [], frame = 0, target = null;
  let activeSurface = null;
  function clearEffects() {
    cancelAnimationFrame(frame);
    frame = 0;
    target = null;
    if (layer) layer.style.opacity = '0';
    if (activeSurface) activeSurface.classList.remove('fx-active');
    activeSurface = null;
  }
  function animateEffects(now) {
    frame = 0;
    if (!target || !layer || document.hidden || dialog?.open) { clearEffects(); return; }
    layer.style.opacity = '1';
    aura.style.transform = `translate3d(${target.x - 220}px, ${target.y - 220}px, 0)`;
    let previous = target;
    particles.forEach((particle, index) => {
      particle.x += (previous.x - particle.x) * 0.32;
      particle.y += (previous.y - particle.y) * 0.32;
      particle.element.style.transform = `translate3d(${particle.x - 6}px, ${particle.y - 6}px, 0) rotate(45deg) scale(${1 - index * 0.055})`;
      particle.element.style.opacity = String(0.85 - index * 0.05);
      previous = particle;
    });
    frame = requestAnimationFrame(animateEffects);
  }
  function moveEffects(event) {
    if (event.pointerType !== 'mouse' || dialog?.open) { clearEffects(); return; }
    if (!target) {
      particles.forEach(particle => { particle.x = event.clientX; particle.y = event.clientY; });
    }
    target = { x: event.clientX, y: event.clientY };
    layer.style.opacity = '1';
    const surface = event.target.closest?.('.fx-surface');
    if (activeSurface !== surface) {
      activeSurface?.classList.remove('fx-active');
      activeSurface = surface;
      activeSurface?.classList.add('fx-active');
    }
    if (surface) {
      const rect = surface.getBoundingClientRect();
      surface.style.setProperty('--surface-x', `${event.clientX - rect.left}px`);
      surface.style.setProperty('--surface-y', `${event.clientY - rect.top}px`);
    }
    layer.classList.toggle('fx-over-link', !!event.target.closest?.('a, button, summary'));
    if (!frame) frame = requestAnimationFrame(animateEffects);
  }
  function syncEffects() {
    clearEffects();
    document.removeEventListener('pointermove', moveEffects);
    layer?.remove(); layer = null; particles = [];
    if (!effectsMedia.matches) return;
    layer = document.createElement('div');
    layer.className = 'pointer-effects';
    layer.setAttribute('aria-hidden', 'true');
    aura = document.createElement('i'); aura.className = 'pointer-aura';
    layer.append(aura);
    for (let index = 0; index < 14; index++) {
      const element = document.createElement('i'); element.className = 'pointer-spark';
      layer.append(element); particles.push({ element, x: 0, y: 0 });
    }
    document.body.append(layer);
    document.addEventListener('pointermove', moveEffects, { passive: true });
  }
  $$('.card,.guide-step,.build-card,.delta-code-card,.delta-world-card,.trust-card,.download-block,.release-glance,.xeno-world-panel,[data-glow]').forEach(surface => {
    surface.classList.add('fx-surface');
    const glow = document.createElement('span');
    glow.className = 'surface-glow'; glow.setAttribute('aria-hidden', 'true');
    surface.append(glow);
  });
  effectsMedia.addEventListener('change', syncEffects);
  document.addEventListener('pointerout', event => { if (!event.relatedTarget) clearEffects(); });
  document.addEventListener('visibilitychange', clearEffects);
  document.addEventListener('pointerdown', clearEffects, { passive: true });
  window.addEventListener('blur', clearEffects);
  window.addEventListener('scroll', clearEffects, { passive: true });
  syncEffects();

  const progress = document.createElement('div');
  progress.className = 'reading-progress'; progress.setAttribute('aria-hidden', 'true');
  document.body.append(progress);
  let scrollFrame = 0;
  function updateProgress() {
    scrollFrame = 0;
    const length = document.documentElement.scrollHeight - innerHeight;
    progress.style.transform = `scaleX(${length > 0 ? Math.min(1, Math.max(0, scrollY / length)) : 0})`;
  }
  function queueProgress() { if (!scrollFrame) scrollFrame = requestAnimationFrame(updateProgress); }
  window.addEventListener('scroll', queueProgress, { passive: true });
  window.addEventListener('resize', queueProgress, { passive: true });
  updateProgress();

  if (siteUrl) {
    let canonical = $('link[rel="canonical"]');
    if (!canonical) { canonical = document.createElement('link'); canonical.rel = 'canonical'; document.head.append(canonical); }
    canonical.href = siteUrl;
  }
  const schema = $('#software-schema');
  if (schema) {
    try {
      const data = JSON.parse(schema.textContent);
      if (siteUrl) data.url = siteUrl;
      if (downloadUrl) data.downloadUrl = downloadUrl;
      if (config.version) data.softwareVersion = config.version;
      if (config.platform) data.operatingSystem = config.platform;
      schema.textContent = JSON.stringify(data);
    } catch { /* A missing schema must not prevent navigation or downloads. */ }
  }

  // Scroll reveal: sections and cards fade in as they enter the viewport.
  const revealTargets = $$('.card,.guide-step,.section-heading,.trust-card,.download-block,.release-glance,.context-strip,.code-window,.faq-list details');
  revealTargets.forEach(el => el.classList.add('reveal'));
  if ('IntersectionObserver' in window) {
    const revealObserver = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-visible');
          revealObserver.unobserve(entry.target);
        }
      });
    }, { threshold: 0.1, rootMargin: '0px 0px -36px 0px' });
    revealTargets.forEach(el => revealObserver.observe(el));
  } else {
    revealTargets.forEach(el => el.classList.add('is-visible'));
  }
})();
