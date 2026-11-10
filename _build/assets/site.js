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

/* Sign bar on phones (hidden while the red band is on screen) + two-version wording test.
   The version rides on every Sign link as ref=fraudbad-a / ref=fraudbad-b so signatures can be split by it. */
(() => {
  let v = 'a';
  try { v = sessionStorage.getItem('fb_v') || (Math.random() < 0.5 ? 'a' : 'b'); sessionStorage.setItem('fb_v', v); }
  catch (e) { v = Math.random() < 0.5 ? 'a' : 'b'; }
  const line = document.querySelector('.cta-line');
  if (v === 'b' && line && line.dataset.b) line.textContent = line.dataset.b;
  document.querySelectorAll('a[href*="america.co/receipts-act"][href*="ref=fraudbad"]').forEach(a => {
    a.href = a.href.replace('ref=fraudbad&', 'ref=fraudbad-' + v + '&');
  });
  const bar = document.querySelector('.signbar'), band = document.querySelector('.cta');
  if (!bar) return;
  let past = false, bandOn = false;
  const show = () => bar.classList.toggle('on', past && !bandOn);
  window.addEventListener('scroll', () => { past = window.scrollY > 600; show(); }, { passive: true });
  if (band && 'IntersectionObserver' in window) new IntersectionObserver(es => { bandOn = es[0].isIntersecting; show(); }).observe(band);
})();

/* Sign without leaving the page (plan 0.7). The build turns the red band's form on only once america.co accepts
   posts from fraudbad.com (build.py checks its preflight); until then the band keeps its plain link to america.co.
   Same fields, consent text and request shape as america.co's own form, plus where the signer came from. */
(() => {
  const form = document.querySelector('[data-inline-sign]'), link = document.querySelector('[data-sign-link]');
  const status = document.querySelector('[data-sign-status]');
  if (!form || form.hidden || !link || !status || !window.fetch || !window.crypto || !crypto.randomUUID) return;
  const API = 'https://america.co/api/newsletter', COUNT = 'https://america.co/api/receipts-act/count';
  const keep = (s) => (s && /^[a-z0-9-]{1,64}$/.test(s) ? s : undefined);
  if (location.hostname === 'fraudbad.com') fetch(COUNT).then(r => (r.ok ? r.json() : null)).then(j => {
    const n = j && j.count;
    if (typeof n === 'number' && n > 0) { const c = form.querySelector('[data-sign-count]'); c.textContent = n.toLocaleString('en-US') + ' people have signed.'; c.hidden = false; }
  }).catch(() => {});
  const button = form.querySelector('button[type="submit"]'), label = button.innerHTML;
  let pending, sending = false;
  const fallback = () => { const a = document.createElement('a'); a.href = link.href; a.rel = 'nofollow'; a.textContent = 'Or sign on America.co'; a.className = 'sign-alt'; status.append(' ', a); };
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (sending || !form.reportValidity()) return;
    const q = new URL(link.href).searchParams;
    const data = Object.fromEntries(new FormData(form));
    data.action = 'subscribe'; data.consent = data.consent === 'on';
    data.source = 'fraudbad.com' + location.pathname.replace(/\.html$/, '').replace(/\/index$/, '/'); data.purpose = 'receipts-act';
    data.ref = keep(q.get('ref')); data.refCase = keep(q.get('case')); data.refPos = 'band';
    const snapshot = JSON.stringify(data);
    if (!pending || pending.snapshot !== snapshot) {
      const bytes = crypto.getRandomValues(new Uint8Array(32));
      pending = { snapshot, id: crypto.randomUUID(), token: Array.from(bytes, x => x.toString(16).padStart(2, '0')).join('') };
    }
    data.requestId = pending.id; data.unsubscribeToken = pending.token;
    sending = true; button.disabled = true; button.textContent = 'Saving…'; form.setAttribute('aria-busy', 'true');
    status.textContent = 'Saving your signup…'; status.dataset.state = 'pending';
    const controller = new AbortController(), timeout = setTimeout(() => controller.abort(), 20000);
    try {
      const response = await fetch(API, { method: 'POST', mode: 'cors', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data), signal: controller.signal });
      const result = await response.json();
      if (!response.ok || result.receipt !== pending.id) throw new Error(result.error || 'We could not confirm your signup. Please try again.');
      status.textContent = 'Thank you. Your support for the working draft is recorded, and your newsletter signup is saved.';
      const ref = document.createElement('span'); ref.className = 'sign-ref'; ref.textContent = 'Reference: ' + result.receipt; status.append(ref);
      if (result.unsubscribeUrl && /^https:\/\/america\.co\/privacy#newsletter=[a-f0-9]{64}$/.test(result.unsubscribeUrl)) {
        const m = document.createElement('a'); m.href = result.unsubscribeUrl; m.rel = 'nofollow'; m.textContent = 'Save your unsubscribe link'; m.className = 'sign-manage'; status.append(m);
      }
      status.dataset.state = 'success'; form.hidden = true;
    } catch (error) {
      status.textContent = error.name === 'AbortError' ? 'The connection timed out. Your details are still here. Retry to confirm; the same request will not create a duplicate.'
        : error.message === 'Failed to fetch' || error instanceof TypeError ? 'Could not connect. Your details are still here. Please try again.'
        : error instanceof SyntaxError ? 'We could not confirm receipt. Please try again.' : error.message;
      status.dataset.state = 'error'; fallback();
    } finally { clearTimeout(timeout); sending = false; button.disabled = false; button.innerHTML = label; form.setAttribute('aria-busy', 'false'); }
  });
})();
