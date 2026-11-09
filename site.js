(() => {
  'use strict';
  const root = document.documentElement;
  root.classList.remove('no-js');
  const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (reduce || !('IntersectionObserver' in window)) root.classList.add('static');

  const onView = (els, fn, threshold = 0.25) => {
    if (root.classList.contains('static')) { els.forEach(fn); return; }
    const io = new IntersectionObserver((entries) => {
      entries.forEach((e) => { if (e.isIntersecting) { io.unobserve(e.target); fn(e.target); } });
    }, { threshold });
    els.forEach((el) => io.observe(el));
  };

  // Receipt prints line by line, then the stamp lands.
  onView([...document.querySelectorAll('.receipt')], (r) => {
    const lines = [...r.querySelectorAll('.r-lines li')];
    lines.forEach((li, i) => setTimeout(() => li.classList.add('in'), 140 + i * 170));
    const stamp = r.querySelector('.stamp');
    if (stamp) setTimeout(() => stamp.classList.add('in'), 260 + lines.length * 170);
  });

  // Transparency dive: rows reveal top to bottom, then a coin drops to where receipts stop.
  const dive = document.querySelector('.dive');
  if (dive) {
    onView([dive], () => {
      const cells = [...dive.querySelectorAll('.cell')];
      cells.forEach((c) => setTimeout(() => c.classList.add('in'), 120 + Number(c.dataset.row || 0) * 230));
      if (root.classList.contains('static') || window.innerWidth < 900) return;
      const box = dive.getBoundingClientRect();
      ['federal', 'state', 'local'].forEach((col, i) => {
        const head = dive.querySelector(`.colhead[data-col="${col}"]`);
        const stop = dive.querySelector(`.cell.stop[data-col="${col}"]`);
        if (!head || !stop || !head.animate) return;
        const h = head.getBoundingClientRect(), s = stop.getBoundingClientRect();
        const coin = document.createElement('span');
        coin.className = 'coin'; coin.textContent = '$'; coin.setAttribute('aria-hidden', 'true');
        const x = h.left - box.left + h.width / 2 - 15;
        const y0 = h.bottom - box.top + 4, y1 = s.top - box.top - 34;
        coin.style.left = x + 'px';
        dive.appendChild(coin);
        coin.animate([
          { transform: `translateY(${y0}px)`, opacity: 0 },
          { transform: `translateY(${y0 + 10}px)`, opacity: 1, offset: 0.08 },
          { transform: `translateY(${y1}px)`, opacity: 1, offset: 0.86 },
          { transform: `translateY(${y1 - 10}px)`, opacity: 1, offset: 0.93 },
          { transform: `translateY(${y1}px)`, opacity: 1 }
        ], { duration: 1500 + i * 160, delay: 500 + i * 220, easing: 'cubic-bezier(.5,0,.75,0)', fill: 'forwards' });
      });
    }, 0.15);
  }

  // Bars fill when seen.
  onView([...document.querySelectorAll('.bar-row')], (b) => b.classList.add('in'), 0.4);

  // Case filters on the home page: kind (hard/soft) x level.
  const chips = [...document.querySelectorAll('.chip[data-group]')];
  const cards = [...document.querySelectorAll('.card[data-level]')];
  const state = { type: 'all', level: 'all' };
  const apply = () => {
    chips.forEach((c) => c.setAttribute('aria-pressed', String(state[c.dataset.group] === c.dataset.filter)));
    cards.forEach((c) => {
      const ok = (state.type === 'all' || c.dataset.type === state.type) && (state.level === 'all' || c.dataset.level === state.level);
      c.hidden = !ok;
    });
  };
  chips.forEach((c) => c.addEventListener('click', () => {
    state[c.dataset.group] = c.dataset.filter; apply();
    const h = [state.type, state.level].filter((v) => v !== 'all').join('-');
    try { history.replaceState(null, '', h ? '#' + h : location.pathname); } catch (_) {}
  }));
  if (chips.length) {
    location.hash.slice(1).split('-').forEach((v) => {
      if (['hard', 'soft'].includes(v)) state.type = v;
      if (['federal', 'state', 'local'].includes(v)) state.level = v;
    });
    apply();
  }

  // Live fraud ticker at GAO's estimated yearly rate.
  const tick = document.querySelector('[data-ticker]');
  if (tick) {
    const lo = 233e9 / 31557600, hi = 521e9 / 31557600; // dollars per second
    const out = tick.querySelector('b');
    const t0 = performance.now();
    const fmt = (n) => '$' + Math.round(n).toLocaleString('en-US');
    const draw = () => {
      const s = (performance.now() - t0) / 1000;
      out.textContent = `${fmt(lo * s)}–${fmt(hi * s)}`;
      if (!reduce) requestAnimationFrame(draw);
    };
    if (reduce) setInterval(draw, 1000);
    draw();
  }

  // Share controls. Only report a copy that actually happened.
  const status = document.querySelector('.share .status');
  const say = (m) => { if (status) status.textContent = m; };
  const copy = async (text) => {
    try { if (navigator.clipboard && window.isSecureContext) { await navigator.clipboard.writeText(text); return true; } } catch (_) {}
    try {
      const ta = document.createElement('textarea');
      ta.value = text; ta.setAttribute('readonly', ''); ta.style.position = 'fixed'; ta.style.opacity = '0';
      document.body.appendChild(ta); ta.select();
      const ok = document.execCommand('copy'); ta.remove(); return ok;
    } catch (_) { return false; }
  };
  document.querySelectorAll('[data-copy]').forEach((b) => b.addEventListener('click', async () => {
    const url = b.dataset.copy;
    say((await copy(url)) ? 'Link copied.' : 'Copy failed — here it is: ' + url);
  }));
  document.querySelectorAll('[data-share]').forEach((b) => {
    if (!navigator.share) { b.hidden = true; return; }
    b.addEventListener('click', () => navigator.share({ title: document.title, url: b.dataset.share }).catch(() => {}));
  });
})();
