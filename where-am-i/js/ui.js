/* Интерфейс: форма ↔ профиль, выбор группы, поэтапный пересчёт и отрисовка. */
(function () {
  'use strict';
  const D = window.DATA;
  const M = window.createModel(D);
  const S = window.Stats;
  const $ = (s, el) => (el || document).querySelector(s);
  const $$ = (s, el) => Array.from((el || document).querySelectorAll(s));
  const esc = s => String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const STORE_KEY = 'where-am-i.profile.v1';

  const state = {
    profile: null,
    group: { region: null, sex: null, age: null, special: 'none' },   // null = «следовать профилю»
    mode: 'strengths', excluded: new Set(), forced: new Set(), sort: 'dAttr',
    gen: 0, lastImpr: [],
  };

  // ---------- форматирование ----------
  const nf = (x, d) => Number(x).toLocaleString('ru-RU', { maximumFractionDigits: d === undefined ? 0 : d, minimumFractionDigits: 0 });
  function pctNum(p) {
    const v = 100 * p;
    if (v >= 99.95) return '>99.9';
    if (v <= 0.05) return '<0.1';
    if (v >= 99 || v <= 1) return nf(v, 1);
    return nf(Math.round(v));
  }
  function topLabel(p) {
    const t = 100 * (1 - p);
    if (t < 0.05) return 'топ <0.1%';
    if (t < 1) return 'топ ' + nf(t, 1) + '%';
    if (p < 0.5) return 'ниже медианы';
    return 'топ ' + nf(Math.round(t)) + '%';
  }
  const SUP = { '0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴', '5': '⁵', '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹', '.': '·', '-': '⁻' };
  function big(n) {
    if (!Number.isFinite(n)) return '∞';
    if (n < 10) return nf(n, 1);
    if (n < 1e3) return nf(Math.round(n));
    if (n < 1e6) return nf(n / 1e3, n < 1e4 ? 1 : 0) + ' тыс.';
    if (n < 1e9) return nf(n / 1e6, n < 1e7 ? 1 : 0) + ' млн';
    if (n < 1e12) return nf(n / 1e9, n < 1e10 ? 1 : 0) + ' млрд';
    if (n < 1e15) return nf(n / 1e12, n < 1e13 ? 1 : 0) + ' трлн';
    const k = Math.log10(n);
    return '10' + nf(k, 1).replace(',', '.').split('').map(c => SUP[c] || c).join('');
  }
  const bigLog = l => big(Math.pow(10, l));
  function money(x) {
    if (x === null || x === undefined) return '';
    const a = Math.abs(x), s = x < 0 ? '−' : '';
    if (a >= 1e9) return s + nf(a / 1e9, 1) + ' млрд ₽';
    if (a >= 1e6) return s + nf(a / 1e6, 1) + ' млн ₽';
    if (a >= 1e3) return s + nf(a / 1e3, 0) + ' тыс. ₽';
    return s + nf(a) + ' ₽';
  }
  function fmtValue(f, o) {
    if (!o) return '';
    const x = o.x;
    if (f.type === 'categorical') return esc(f.categories[x].label);
    if (f.id === 'income' || f.id === 'networth') return money(x) + (f.id === 'income' ? '/мес' : '');
    if (f.id === 'bench' || f.id === 'squat') return nf(o.rawKg, 1) + ' кг = ' + nf(x, 2) + '× вес';
    if (f.id === 'bmi') return nf(x, 1);
    if (f.id === 'vo2') return nf(x, 1) + ' ' + f.unit;
    if (f.id === 'face') return nf(x, 1) + ' /10';
    return nf(x, 1) + (f.unit ? ' ' + f.unit : '');
  }
  function css(v) { return getComputedStyle(document.documentElement).getPropertyValue(v).trim(); }
  function hexToRgb(h) { h = h.replace('#', ''); if (h.length === 3) h = h.split('').map(c => c + c).join(''); const n = parseInt(h, 16); return [(n >> 16) & 255, (n >> 8) & 255, n & 255]; }
  function mix(a, b, t) { const A = hexToRgb(a), B = hexToRgb(b); return 'rgb(' + A.map((v, i) => Math.round(v + (B[i] - v) * t)).join(',') + ')'; }
  function divColor(p) { // p ∈ [0,1], 0.5 → нейтрально
    const neg = css('--div-neg'), mid = css('--div-mid'), pos = css('--div-pos');
    const t = Math.min(1, Math.abs(p - 0.5) * 2);
    const e = Math.pow(t, 0.8) * 0.85;
    return p >= 0.5 ? mix(mid, pos, e) : mix(mid, neg, e);
  }
  function divText(p) { return Math.abs(p - 0.5) > 0.36 ? '#fff' : css('--text'); }
  const tick = () => new Promise(r => setTimeout(r, 0));

  // ---------- форма ----------
  function fieldHtml(f) {
    const id = 'in-' + f.id;
    let ctl;
    if (f.input.kind === 'select') {
      ctl = `<select id="${id}" data-key="${f.id}"><option value="">— не указано —</option>${f.categories.map(c => `<option value="${esc(c.id)}">${esc(c.label)}</option>`).join('')}</select>`;
    } else {
      const i = f.input;
      ctl = `<input type="number" id="${id}" data-key="${f.id}" min="${i.min}" max="${i.max}" step="${i.step}" placeholder="${esc(i.placeholder || '')}" inputmode="decimal"><span class="unit">${esc(f.unit || '')}</span>`;
    }
    let sub = '';
    if (f.alt) sub += `<input type="number" data-key="${f.alt.key}" min="${f.alt.min}" max="${f.alt.max}" step="${f.alt.step}" placeholder="${esc(f.alt.label)}" title="${esc(f.alt.label)}">`;
    if (f.method) sub += `<select data-key="${f.method.key}" title="${esc(f.method.label)}">${f.method.options.map(o => `<option value="${o.id}"${o.id === f.method.default ? ' selected' : ''}>${esc(o.label)}</option>`).join('')}</select>`;
    const hint = f.categoryNote || (f.method && f.method.note) || '';
    return `<div class="field"><label for="${id}">${esc(f.label)}</label><div class="row">${ctl}</div>${sub ? `<div class="sub">${sub}</div>` : ''}${hint ? `<div class="hint">${esc(hint)}</div>` : ''}</div>`;
  }
  function buildForm() {
    let html = '';
    for (const sec of D.sections) {
      html += `<fieldset class="sec"><legend>${esc(sec.label)}</legend>`;
      if (sec.id === 'about') {
        html += `<div class="field"><label for="in-name">Название профиля</label><div class="row"><input type="text" id="in-name" data-about="name" placeholder="я, ноябрь 2026"></div></div>`;
        html += `<div class="field"><label for="in-sex">Пол</label><div class="row"><select id="in-sex" data-about="sex"><option value="male">Мужской</option><option value="female">Женский</option></select></div></div>`;
        html += `<div class="field"><label for="in-age">Возраст</label><div class="row"><input type="number" id="in-age" data-about="age" min="16" max="80" step="1" placeholder="27"><span class="unit">лет</span></div></div>`;
        html += `<div class="field"><label for="in-home">Где живёшь (группа по умолчанию)</label><div class="row"><select id="in-home" data-about="home">${D.groups.regions.map(r => `<option value="${r.id}">${esc(r.label)}</option>`).join('')}</select></div></div>`;
      }
      for (const f of D.features.filter(x => x.section === sec.id && !x.derived)) {
        html += fieldHtml(f);
        if (f.id === 'height') html += `<div class="field"><label for="in-weight">Вес</label><div class="row"><input type="number" id="in-weight" data-key="weight" min="35" max="250" step="0.5" placeholder="78" inputmode="decimal"><span class="unit">кг</span></div><div class="hint">Нужен для ИМТ, силы относительно веса и оценки % жира.</div></div>`;
      }
      html += '</fieldset>';
    }
    $('#form').innerHTML = html;
  }
  function readForm() {
    const p = { version: 1, values: {} };
    $$('[data-about]').forEach(el => { p[el.dataset.about] = el.dataset.about === 'age' ? (el.value === '' ? '' : Number(el.value)) : el.value; });
    $$('[data-key]').forEach(el => { const v = el.value; p.values[el.dataset.key] = el.type === 'number' ? (v === '' ? '' : Number(v)) : v; });
    return p;
  }
  function writeForm(p) {
    p = p || { values: {} };
    $$('[data-about]').forEach(el => {
      const v = p[el.dataset.about];
      if (el.tagName === 'SELECT') el.value = v || el.options[0].value; else el.value = v === undefined || v === null ? '' : v;
    });
    $$('[data-key]').forEach(el => {
      const v = (p.values || {})[el.dataset.key];
      if (el.tagName === 'SELECT') {
        const f = D.features.find(x => x.method && x.method.key === el.dataset.key);
        el.value = v !== undefined && v !== null && v !== '' ? v : (f ? f.method.default : '');
      } else el.value = v === undefined || v === null ? '' : v;
    });
  }
  function save() { try { localStorage.setItem(STORE_KEY, JSON.stringify(state.profile)); } catch (e) { /* приватный режим */ } }
  function loadStored() { try { const s = localStorage.getItem(STORE_KEY); return s ? JSON.parse(s) : null; } catch (e) { return null; } }

  // ---------- группа ----------
  function userBand() { return M.ageBand(Number(state.profile.age) || 30); }
  function groupSpec() {
    const p = state.profile;
    return {
      region: state.group.region || p.home || 'russia',
      sex: state.group.sex || (p.sex === 'female' ? 'female' : 'male'),
      age: state.group.age || userBand(),
      special: state.group.special,
    };
  }
  function segButtons(el, items, current, onClick, disabled) {
    el.innerHTML = items.map(it => `<button type="button" data-v="${it.id}" aria-pressed="${it.id === current}"${disabled ? ' disabled' : ''}>${esc(it.label)}${it.mine ? '<span class="dot" title="твоя группа"></span>' : ''}</button>`).join('');
    $$('button', el).forEach(b => b.addEventListener('click', () => onClick(b.dataset.v)));
  }
  function renderGroupBar() {
    const g = groupSpec(), topuni = g.special === 'topuni', band = userBand();
    segButtons($('#seg-region'), D.groups.regions.map(r => Object.assign({ mine: r.id === state.profile.home }, r)), topuni ? 'moscow' : g.region, v => { state.group.region = v; update(); }, topuni);
    segButtons($('#seg-sex'), D.groups.sexes.map(s => Object.assign({ mine: s.id === state.profile.sex }, s)), g.sex, v => { state.group.sex = v; update(); });
    const ages = [{ id: 'all', label: '18–64' }].concat(D.groups.ages.map(a => ({ id: a.id, label: a.label, mine: a.id === band })));
    segButtons($('#seg-age'), ages, topuni ? '18-24' : g.age, v => { state.group.age = v; update(); }, topuni);
    $('#chk-topuni').checked = topuni;
    $$('#seg-mode button').forEach(b => b.setAttribute('aria-pressed', b.dataset.mode === state.mode));
    $$('#seg-sort button').forEach(b => b.setAttribute('aria-pressed', b.dataset.sort === state.sort));
  }

  // ---------- графики ----------
  function lognormalRange(margs) {
    let lo = Infinity, hi = -Infinity;
    for (const m of margs) { lo = Math.min(lo, m.mu - 3 * m.sigma); hi = Math.max(hi, m.mu + 3.2 * m.sigma); }
    return [lo / Math.LN10, hi / Math.LN10];
  }
  function niceLogTicks(a, b) { const out = []; for (let k = Math.ceil(a); k <= Math.floor(b); k++) out.push(k); return out; }
  function tickLabelLog(f, k) {
    const v = Math.pow(10, k);
    if (f.id === 'income' || f.id === 'networth') return v >= 1e6 ? nf(v / 1e6) + ' млн' : v >= 1e3 ? nf(v / 1e3) + ' тыс' : nf(v);
    return v >= 1e6 ? nf(v / 1e6) + 'M' : v >= 1e3 ? nf(v / 1e3) + 'k' : nf(v);
  }

  function densityChart(f, group, res) {
    const cells = group.cells.map(c => ({ c, m: M.marginal(f, c) })).filter(x => x.m);
    const wsum = cells.reduce((s, x) => s + x.c.w, 0);
    const W = 300, H = 92, pl = 4, pr = 4, pt = 14, pb = 18;
    const isLog = f.type === 'lognormal' && cells[0].m.sigma >= 0.6;
    let x0, x1, ux = null;
    const ratio = (f.id === 'bench' || f.id === 'squat');
    if (isLog) {
      [x0, x1] = lognormalRange(cells.map(x => x.m));
      if (res && res.x > 0) { ux = Math.log10(res.x); x0 = Math.min(x0, ux - 0.2); x1 = Math.max(x1, ux + 0.2); }
    } else {
      x0 = Infinity; x1 = -Infinity;
      for (const { m } of cells) { x0 = Math.min(x0, m.quantile(0.003)); x1 = Math.max(x1, m.quantile(0.997)); }
      if (f.type === 'lognormal') x0 = Math.max(0, x0);
      if (res) { ux = res.x; x0 = Math.min(x0, ux - (x1 - x0) * 0.04); x1 = Math.max(x1, ux + (x1 - x0) * 0.04); }
    }
    const n = 120, pts = [];
    let ymax = 0;
    for (let i = 0; i <= n; i++) {
      const xv = x0 + (x1 - x0) * i / n;
      let y = 0;
      for (const { c, m } of cells) {
        if (isLog) { const x = Math.pow(10, xv); y += c.w / wsum * m.pdf(x) * x * Math.LN10; }
        else y += c.w / wsum * m.pdf(xv);
      }
      pts.push([xv, y]); ymax = Math.max(ymax, y);
    }
    const sx = v => pl + (W - pl - pr) * (v - x0) / (x1 - x0);
    const sy = v => H - pb - (H - pb - pt) * v / (ymax * 1.05);
    const line = pts.map((p, i) => (i ? 'L' : 'M') + sx(p[0]).toFixed(1) + ' ' + sy(p[1]).toFixed(1)).join('');
    const area = line + `L${sx(x1).toFixed(1)} ${sy(0)}L${sx(x0).toFixed(1)} ${sy(0)}Z`;
    let shade = '';
    if (ux !== null) {
      // закрашиваем долю группы, которая «хуже» тебя (для «меньше = лучше» — справа)
      const worseLeft = f.direction !== 'lower';
      const yAt = xv => { for (let i = 1; i < pts.length; i++) if (pts[i][0] >= xv) { const [xa, ya] = pts[i - 1], [xb, yb] = pts[i]; return ya + (yb - ya) * (xv - xa) / (xb - xa || 1); } return 0; };
      const inner = pts.filter(p => (worseLeft ? p[0] < ux : p[0] > ux));
      const poly = worseLeft ? [[x0, 0]].concat(inner, [[ux, yAt(ux)], [ux, 0]]) : [[ux, 0], [ux, yAt(ux)]].concat(inner, [[x1, 0]]);
      shade = `<path d="${poly.map((p, i) => (i ? 'L' : 'M') + sx(p[0]).toFixed(1) + ' ' + sy(p[1]).toFixed(1)).join('')}Z" fill="var(--s1-soft)"/>`;
    }
    // оси: 3–5 подписей
    let ticks = '';
    if (isLog) {
      for (const k of niceLogTicks(x0, x1)) ticks += `<text x="${sx(k).toFixed(1)}" y="${H - 4}" font-size="9.5" text-anchor="middle">${tickLabelLog(f, k)}</text>`;
    } else {
      const span = x1 - x0, step = [0.05, 0.1, 0.2, 0.25, 0.5, 1, 2, 5, 10, 20, 25, 50].find(s => span / s <= 5) || 100;
      for (let v = Math.ceil(x0 / step) * step; v <= x1; v += step) ticks += `<text x="${sx(v).toFixed(1)}" y="${H - 4}" font-size="9.5" text-anchor="middle">${nf(v, step < 1 ? 2 : 0)}${ratio ? '×' : ''}</text>`;
    }
    let marker = '';
    if (ux !== null) {
      const X = sx(ux).toFixed(1);
      const anchor = sx(ux) > W - 30 ? 'end' : sx(ux) < 30 ? 'start' : 'middle';
      const lx = anchor === 'end' ? sx(ux) - 5 : sx(ux) + 5;
      marker = `<line x1="${X}" x2="${X}" y1="${pt - 6}" y2="${sy(0)}" stroke="var(--s1)" stroke-width="2"/><text x="${lx.toFixed(1)}" y="${pt}" font-size="10.5" text-anchor="${anchor === 'end' ? 'end' : 'start'}" class="lbl-strong">ты</text>`;
    }
    // невидимые полосы для подсказок
    let hits = '';
    const nb = 30;
    for (let i = 0; i < nb; i++) {
      const xv = x0 + (x1 - x0) * (i + 0.5) / nb;
      const raw = isLog ? Math.pow(10, xv) : xv;
      const g = M.groupWorse(f, group, raw);
      if (!g) continue;
      const label = isLog ? (f.id === 'income' || f.id === 'networth' ? money(raw) : nf(raw, raw < 10 ? 1 : 0)) : nf(raw, ratio ? 2 : 1) + (ratio ? '× вес' : f.unit ? ' ' + f.unit : '');
      hits += `<rect x="${sx(x0 + (x1 - x0) * i / nb).toFixed(1)}" y="0" width="${((W - pl - pr) / nb).toFixed(1)}" height="${H}" fill="transparent" data-tip="${esc(label + '\nперцентиль ' + pctNum((g.lo + g.hi) / 2))}"/>`;
    }
    const zeroNote = isLog && cells[0].m.p0 > 0.005 ? `<text x="${pl}" y="10" font-size="9.5">0: ${pctNum(cells.reduce((s, x) => s + x.c.w * x.m.p0, 0) / wsum)}%</text>` : '';
    return `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Распределение: ${esc(f.label)}"><path d="${area}" fill="var(--s1-softer)"/>${shade}<path d="${line}" fill="none" stroke="var(--s1)" stroke-width="1.5" opacity="0.75"/><line x1="${pl}" x2="${W - pr}" y1="${sy(0)}" y2="${sy(0)}" class="grid"/>${ticks}${zeroNote}${marker}${hits}</svg>`;
  }
  function catBars(f, group, res) {
    const cells = group.cells.map(c => ({ c, m: M.marginal(f, c) })).filter(x => x.m);
    const wsum = cells.reduce((s, x) => s + x.c.w, 0);
    const probs = f.categories.map((_, k) => cells.reduce((s, x) => s + x.c.w * x.m.probs[k], 0) / wsum);
    const mx = Math.max(...probs);
    return `<div class="catbars">${f.categories.slice().map((c, k) => ({ c, k })).reverse().map(({ c, k }) =>
      `<div class="catrow${res && res.x === k ? ' me' : ''}" data-tip="${esc(c.label + '\n' + pctNum(probs[k]) + '% группы')}"><span class="cl">${res && res.x === k ? '▸ ' : ''}${esc(c.label)}</span><span><span class="cb" style="display:block;width:${Math.max(1, 100 * probs[k] / mx).toFixed(1)}%"></span></span><span class="cp">${pctNum(probs[k])}%</span></div>`).join('')}</div>`;
  }
  function relBadge(rel) {
    const r = D.reliability[rel] || D.reliability.rough;
    const ic = { good: '●', extrap: '◐', rough: '○', na: '–' }[rel] || '○';
    return `<span class="rel rel-${rel}" title="${esc(r.label)}"><span class="ic">${ic}</span>${esc(r.label)}</span>`;
  }
  function sourcesList(ids) {
    return '<ul>' + ids.map(id => { const s = D.sources[id]; return s ? `<li>${esc(s.t)}${s.u ? ` <a href="${esc(s.u)}" target="_blank" rel="noopener">ссылка</a>` : ''}</li>` : ''; }).join('') + '</ul>';
  }

  // ---------- блоки результатов ----------
  function renderFeatures(fr, group, fids) {
    let html = '';
    for (const sec of D.sections) {
      const items = fr.filter(r => r.f.section === sec.id);
      if (!items.length) continue;
      html += `<div class="fsec-title">${esc(sec.label)}</div><div class="fgrid">`;
      for (const r of items) {
        const f = r.f;
        const inN = fids.includes(f.id);
        const canToggle = r.status === 'ok' && !f.descriptive;
        let body = '';
        if (r.status === 'na') body = `<div class="fval muted">Для этой группы нет данных или признак не применим.</div>`;
        else if (r.status === 'missing') body = `<div class="fval muted">Не заполнено.</div>`;
        else {
          const notes = [];
          if (r.obs.estimated) notes.push(r.obs.estimated);
          if (r.obs.adjusted) notes.push('поправка на источник оценки: ' + (r.obs.adjusted > 0 ? '+' : '') + nf(r.obs.adjusted, 1));
          body = `<div class="fval">${fmtValue(f, r.obs)}${notes.length ? ` <span class="muted">(${esc(notes.join('; '))})</span>` : ''}</div>
            <div class="fpct"><b>${pctNum(r.pct)}</b>-й перцентиль <span class="ci">[${pctNum(r.ci[0])}–${pctNum(r.ci[1])}]</span>${f.descriptive ? '' : ' · ' + topLabel(r.pct)}</div>`;
        }
        const chart = r.status === 'na' ? '' : f.type === 'categorical' ? catBars(f, group, r.status === 'ok' ? r : null) : densityChart(f, group, r.status === 'ok' ? r : null);
        html += `<div class="fcard ${r.status}">
          <div class="fhead"><span class="fname">${esc(f.label)}</span>${canToggle ? `<label class="incl" title="Учитывать в «один из N»"><input type="checkbox" data-incl="${f.id}"${inN ? ' checked' : ''}> в N</label>` : ''}</div>
          ${body}${relBadge(r.reliability)}${chart}
          <details><summary>Откуда цифра</summary><p>${esc(f.note || '')}</p>${sourcesList(f.sources || [])}</details></div>`;
      }
      html += '</div>';
    }
    $('#features').innerHTML = html;
    $$('[data-incl]').forEach(cb => cb.addEventListener('change', () => {
      const id = cb.dataset.incl;
      if (cb.checked) { state.excluded.delete(id); state.forced.add(id); } else { state.excluded.add(id); state.forced.delete(id); }
      update();
    }));
  }

  function renderStrengths(fr) {
    const ok = fr.filter(r => r.status === 'ok' && !r.f.descriptive).sort((a, b) => b.pct - a.pct);
    if (!ok.length) { $('#sw').innerHTML = '<p class="muted">Заполни хотя бы несколько полей.</p>'; return; }
    const item = r => `<div class="sw-item"><span>${esc(r.f.short || r.f.label)} <span class="muted">${relIcon(r.reliability)}</span></span><span class="p">${pctNum(r.pct)}-й · ${topLabel(r.pct)}</span></div>`;
    const top = ok.slice(0, Math.min(5, Math.ceil(ok.length / 2)));
    const bottom = ok.slice().reverse().slice(0, Math.min(5, Math.floor(ok.length / 2)));
    $('#sw').innerHTML = `<div class="sw-cols"><div><h3>Сильнее всего</h3>${top.map(item).join('')}</div><div><h3>Слабее всего</h3>${bottom.map(item).join('')}</div></div>
      <p class="explain" style="margin-top:10px">Значки: ● хорошие данные, ◐ экстраполяция, ○ грубая оценка. Перцентиль по признаку с «○» — ориентир, а не измерение.</p>`;
  }
  const relIcon = rel => ({ good: '●', extrap: '◐', rough: '○' }[rel] || '');

  function renderRarity(rar, fids, group, fr) {
    const modeTxt = state.mode === 'strengths'
      ? `Считаем долю людей группы, которые <b>не хуже тебя одновременно по всем ${fids.length} признакам, где ты выше медианы</b> (можно править галочками «в N»).`
      : `Считаем долю людей группы, которые <b>не хуже тебя одновременно по всем ${fids.length} заполненным признакам</b>. Чем больше признаков, тем больше N почти у любого — см. методологию.`;
    $('#rarity-def').innerHTML = modeTxt;
    if (!rar) { $('#rarity-tiles').innerHTML = '<p class="muted">Нет признаков для расчёта: заполни форму или включи признаки галочками.</p>'; $('#rarity-why').innerHTML = ''; return; }
    const ratio = rar.honest / rar.naive;
    const nH = 1 / rar.honest, count = group.size * rar.honest;
    const cnt = count < 1 ? `ожидается ${nf(count, count < 0.1 ? 2 : 1)} — то есть, вероятно, никого` : `≈ ${big(count)} чел.`;
    $('#rarity-tiles').innerHTML = `
      <div class="tile"><div class="k"><span class="sw" style="background:var(--s2)"></span>Наивно (признаки независимы)</div>
        <div class="v">1 из ${big(1 / rar.naive)}</div><div class="r">интервал: 1 из ${bigLog(rar.naiveCI[0])} … ${bigLog(rar.naiveCI[1])}</div></div>
      <div class="tile"><div class="k"><span class="sw" style="background:var(--s1)"></span>С учётом корреляций</div>
        <div class="v">1 из ${big(nH)}</div><div class="r">интервал: 1 из ${bigLog(rar.honestCI[0])} … ${bigLog(rar.honestCI[1])}</div></div>
      <div class="tile ratio"><div class="k">Наивный счёт завышает редкость</div>
        <div class="v">в ${big(ratio)} раз</div><div class="r">В группе «${esc(group.label)}» (≈ ${big(group.size)} чел.) не хуже тебя по всем этим признакам: ${cnt}.</div></div>`;
    // объяснение: самые коррелированные пары среди выбранных
    const R = M.corrMatrix(1), pairs = [];
    for (let i = 0; i < fids.length; i++) for (let j = i + 1; j < fids.length; j++) pairs.push([fids[i], fids[j], R[M.copIndex[fids[i]]][M.copIndex[fids[j]]]]);
    pairs.sort((a, b) => b[2] - a[2]);
    const name = id => (M.byId[id].short || M.byId[id].label).toLowerCase();
    const topPairs = pairs.filter(p => p[2] >= 0.3).slice(0, 4).map(p => `${name(p[0])} ↔ ${name(p[1])} (r = ${nf(p[2], 2)})`);
    const mixed = group.cells.length > 1 ? ' Плюс группа смешанная: пол и возраст сами связывают признаки (у мужчин выше и рост, и сила; с возрастом растут и доход, и активы), и честный счёт это тоже учитывает.' : '';
    $('#rarity-why').innerHTML = topPairs.length
      ? `<b>Почему разница:</b> наивный счёт считает каждый признак новым «фильтром». На деле многие из них измеряют почти одно и то же: ${esc(topPairs.join(', '))}. Если ты прошёл один фильтр, другой ты пройдёшь с большей вероятностью, поэтому вместе они отсеивают меньше людей.${mixed}`
      : `<b>Почему разница небольшая:</b> выбранные признаки почти не связаны между собой.${mixed}`;
  }

  function renderCurve(curve) {
    const el = $('#rarity-curve');
    if (!curve.length) { el.innerHTML = ''; return; }
    const rowH = 22, padT = 26, padL = 128, padR = 70, W = 760;
    const H = padT + rowH * curve.length + 26;
    const ln = curve.map(c => -Math.log10(c.naive)), lh = curve.map(c => -Math.log10(Math.max(c.honest, 1e-300)));
    const xmax = Math.max(1, Math.ceil(Math.max(...ln) + 0.3));
    const sx = v => padL + (W - padL - padR) * v / xmax;
    let g = '';
    const step = xmax > 12 ? 2 : 1;
    for (let k = 0; k <= xmax; k += step) {
      g += `<line x1="${sx(k)}" x2="${sx(k)}" y1="${padT - 6}" y2="${H - 22}" class="grid"/><text x="${sx(k)}" y="${H - 8}" font-size="10.5" text-anchor="middle">${k === 0 ? '1' : bigLog(k)}</text>`;
    }
    curve.forEach((c, i) => {
      const y = padT + rowH * i + rowH / 2;
      const f = M.byId[c.id];
      const x1 = sx(lh[i]), x2 = sx(ln[i]);
      const tip = `+ ${f.short || f.label} (не хуже тебя ${pctNum(c.P)}%)\nнаивно: 1 из ${big(1 / c.naive)}\nс корреляциями: 1 из ${big(1 / c.honest)}`;
      g += `<text x="${padL - 8}" y="${y + 4}" font-size="11.5" text-anchor="end">+ ${esc(f.short || f.label)}</text>`;
      g += `<line x1="${x1}" x2="${x2}" y1="${y}" y2="${y}" stroke="var(--neutral-mark)" stroke-width="2"/>`;
      g += `<circle cx="${x2}" cy="${y}" r="4.5" fill="var(--s2)" stroke="var(--surface)" stroke-width="2"/>`;
      g += `<circle cx="${x1}" cy="${y}" r="4.5" fill="var(--s1)" stroke="var(--surface)" stroke-width="2"/>`;
      g += `<rect x="0" y="${y - rowH / 2}" width="${W}" height="${rowH}" fill="transparent" data-tip="${esc(tip)}"/>`;
    });
    const last = curve.length - 1, yl = padT + rowH * last + rowH / 2;
    g += `<text x="${sx(ln[last]) + 9}" y="${yl + 4}" font-size="11" class="lbl-strong">${big(1 / curve[last].naive)}</text>`;
    if (sx(ln[last]) - sx(lh[last]) > 70) g += `<text x="${sx(lh[last]) + 9}" y="${yl - 7}" font-size="11" class="lbl-strong">${big(1 / curve[last].honest)}</text>`;
    const legend = `<g font-size="11.5"><circle cx="${padL}" cy="10" r="4.5" fill="var(--s1)"/><text x="${padL + 9}" y="14">с корреляциями</text><circle cx="${padL + 120}" cy="10" r="4.5" fill="var(--s2)"/><text x="${padL + 129}" y="14">наивно (произведение)</text><text x="${W - padR}" y="14" text-anchor="end">«один из N»</text></g>`;
    el.innerHTML = `<svg viewBox="0 0 ${W} ${H}" style="min-width:560px" role="img" aria-label="Накопление редкости по признакам">${legend}${g}</svg>`;
  }

  function intervalBar(res) {
    const W = 420, H = 34, pl = 6, pr = 6, y = 14;
    const sx = p => pl + (W - pl - pr) * p;
    let t = '';
    for (const p of [0, 0.25, 0.5, 0.75, 1]) t += `<line x1="${sx(p)}" x2="${sx(p)}" y1="${y - 6}" y2="${y + 6}" class="grid"/><text x="${sx(p)}" y="${H - 2}" font-size="9.5" text-anchor="${p === 0 ? 'start' : p === 1 ? 'end' : 'middle'}">${Math.round(p * 100)}</text>`;
    return `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Перцентиль с интервалом"><line x1="${sx(0)}" x2="${sx(1)}" y1="${y}" y2="${y}" stroke="var(--border)" stroke-width="6" stroke-linecap="round"/>${t}
      <line x1="${sx(res.ci[0])}" x2="${sx(res.ci[1])}" y1="${y}" y2="${y}" stroke="var(--s1-soft)" stroke-width="10" stroke-linecap="round"/>
      <circle cx="${sx(res.pct)}" cy="${y}" r="6" fill="var(--s1)" stroke="var(--surface)" stroke-width="2" data-tip="${esc('оценка: ' + pctNum(res.pct) + '-й перцентиль\n80%-й интервал: ' + pctNum(res.ci[0]) + '–' + pctNum(res.ci[1]))}"/></svg>`;
  }
  function contribChart(contribs) {
    const rows = contribs.filter(c => c.id !== 'penalty' || Math.abs(c.contrib) > 1e-6);
    const W = 420, rowH = 20, padL = 128, padR = 54, H = rowH * rows.length + 8;
    const m = Math.max(0.02, ...rows.map(c => Math.abs(c.dPct)));
    const cx = padL + (W - padL - padR) / 2, half = (W - padL - padR) / 2;
    let g = `<line x1="${cx}" x2="${cx}" y1="0" y2="${H}" class="grid"/>`;
    rows.forEach((c, i) => {
      const y = i * rowH + 4, w = half * Math.abs(c.dPct) / m;
      const pos = c.dPct >= 0;
      const x = pos ? cx : cx - w;
      const lbl = c.short;
      const vtxt = Math.abs(c.dPct) < 0.005 ? '0' : (pos ? '+' : '−') + nf(Math.abs(c.dPct) * 100, 0);
      g += `<text x="${padL - 8}" y="${y + 11}" font-size="11" text-anchor="end">${esc(lbl)}</text>`;
      g += `<rect x="${x.toFixed(1)}" y="${y + 2}" width="${Math.max(1, w).toFixed(1)}" height="${rowH - 8}" rx="3" fill="${pos ? 'var(--div-pos)' : 'var(--div-neg)'}"/>`;
      g += `<text x="${pos ? cx + w + 4 : cx - w - 4}" y="${y + 11}" font-size="10.5" text-anchor="${pos ? 'start' : 'end'}">${vtxt}</text>`;
      g += `<rect x="0" y="${y}" width="${W}" height="${rowH}" fill="transparent" data-tip="${esc(c.label + '\nесли бы эта часть была как у медианного: ' + (pos ? '−' : '+') + nf(Math.abs(c.dPct) * 100, 1) + ' п.п. перцентиля\nвес в индексе ' + (c.id === 'penalty' ? '—' : nf(c.weight * 100) + '%'))}"/>`;
    });
    return `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Вклад компонент">${g}</svg>`;
  }
  function renderIndex(kind, res) {
    const el = $(kind === 'attr' ? '#sec-attr' : '#sec-ses');
    const spec = kind === 'attr' ? D.attractiveness : D.ses;
    const title = kind === 'attr' ? 'Конвенциональная привлекательность для женщин' : 'Положение в социальной иерархии (SES)';
    const who = kind === 'attr' ? 'среди мужчин: ' + esc(res.group.label) : 'среди: ' + esc(res.group.label);
    const confCls = { 'высокая': 'c-high', 'средняя': 'c-mid', 'низкая': 'c-low' }[res.conf];
    const confIc = { 'высокая': '●', 'средняя': '◐', 'низкая': '○' }[res.conf];
    const miss = res.missing.length ? `<p class="subline">Не заполнено и заменено ожиданием по остальным данным: ${res.missing.map(id => esc((M.byId[id].short || M.byId[id].label).toLowerCase())).join(', ')}. Это расширяет интервал.</p>` : '';
    const att = kind === 'attr' ? `<p class="subline">≈ <b>×${nf(res.attention.point, 1)}</b> внимания (лайков/мэтчей) на дейтинг-приложениях к медианному мужчине; интервал ×${nf(res.attention.ci[0], 1)}–${nf(res.attention.ci[1], 1)}. Пересчёт через неравенство лайков (Джини ≈ 0.58) — грубая оценка.</p>` : '';
    const female = kind === 'attr' && state.profile.sex === 'female' ? `<p class="subline">Индекс построен для мужчин по исследованиям женских предпочтений, поэтому твой профиль сравнивается с мужчинами.</p>` : '';
    el.innerHTML = `<h2>${title}</h2><p class="subline">Перцентиль ${who}</p>
      <div class="index-big"><span class="v">${pctNum(res.pct)}</span><span class="u">-й перцентиль · ${topLabel(res.pct)}</span>
      <span class="conf ${confCls}"><span class="ic">${confIc}</span>уверенность: ${res.conf}</span></div>
      <p class="subline">80%-й интервал: ${pctNum(res.ci[0])}–${pctNum(res.ci[1])}</p>${intervalBar(res)}${att}${female}
      <h3 class="h3">Что тянет вверх и вниз, п.п. перцентиля</h3><p class="explain">На сколько пунктов изменилось бы твоё место, если бы эта часть была как у медианного человека группы.</p>${contribChart(res.contributions)}${miss}
      <details><summary>Как устроен индекс и чего он не знает</summary><ul>${spec.caveats.map(c => `<li>${esc(c)}</li>`).join('')}</ul>
      ${kind === 'attr' ? '<p>Компоненты и веса: ' + spec.components.map(c => esc(c.label) + ' — ' + nf(c.weight * 100) + '%').join('; ') + '. Штрафы: ' + spec.penalties.map(p => esc(p.label) + ' ' + nf(p.value, 2)).join(', ') + '.</p>' : '<p>Веса: ' + spec.components.map(c => esc(c.label) + ' — ' + nf(c.weight * 100) + '%').join('; ') + '.</p>'}
      ${sourcesList(spec.sources)}</details>`;
  }
  function renderIndexPending(kind) {
    const el = $(kind === 'attr' ? '#sec-attr' : '#sec-ses');
    if (!el.innerHTML) el.innerHTML = `<h2>${kind === 'attr' ? 'Конвенциональная привлекательность для женщин' : 'Положение в социальной иерархии (SES)'}</h2><p class="muted">Считаю…</p>`;
  }

  function renderImprovements(list) {
    state.lastImpr = list;
    const key = state.sort;
    const rows = list.slice().sort((a, b) => b[key] - a[key]).filter(r => Math.abs(r.dAttr) > 0.0005 || Math.abs(r.dSes) > 0.0005 || r.dLogN > 0.005);
    if (!rows.length) { $('#impr').innerHTML = '<p class="muted">Нечего улучшать: заполни изменяемые признаки.</p>'; return; }
    const mx = Math.max(1e-9, ...rows.map(r => Math.max(0, r[key])));
    const cell = (r, k) => {
      const v = r[k];
      const txt = k === 'dLogN' ? (v > 0.005 ? '×' + big(Math.pow(10, v)) : '—') : (Math.abs(v) < 0.0005 ? '—' : (v > 0 ? '+' : '−') + nf(Math.abs(v) * 100, 1));
      const bar = k === key && v > 0 ? `<span class="b" style="width:${(40 * v / mx).toFixed(1)}px"></span>` : '';
      return `<td class="n"><div class="barcell">${bar}<span>${txt}</span></div></td>`;
    };
    $('#impr').innerHTML = `<div class="table-scroll"><table class="t"><thead><tr><th>Шаг</th><th class="n">Привлекат., п.п.</th><th class="n">Положение, п.п.</th><th class="n">Редкость</th></tr></thead><tbody>
      ${rows.map((r, i) => `<tr class="${i === 0 ? 'best' : ''}"><td>${esc(r.label)}<div class="effort">${esc(r.effort || '')} · перцентиль признака ${r.dPct >= 0 ? '+' : '−'}${nf(Math.abs(r.dPct) * 100, 1)} п.п.</div></td>${cell(r, 'dAttr')}${cell(r, 'dSes')}${cell(r, 'dLogN')}</tr>`).join('')}
      </tbody></table></div><p class="explain" style="margin-top:8px">«Редкость» показывает, во сколько раз вырастет N (с корреляциями). Эффекты считаются по точечной оценке, без интервалов: это сравнение шагов между собой, а не прогноз.</p>`;
  }

  // ---------- сравнение групп ----------
  function comparisonSpecs() {
    const p = state.profile, sex = p.sex === 'female' ? 'female' : 'male', band = userBand();
    const sl = sex === 'male' ? 'муж.' : 'жен.';
    const al = D.groups.ages.find(a => a.id === band).label;
    const list = [
      { s: { region: 'world', sex: 'all', age: 'all' }, l: 'Мир · все' },
      { s: { region: 'world', sex, age: band }, l: `Мир · ${sl} ${al}` },
      { s: { region: 'russia', sex: 'all', age: 'all' }, l: 'Россия · все' },
      { s: { region: 'russia', sex, age: 'all' }, l: `Россия · ${sl}` },
      { s: { region: 'russia', sex, age: band }, l: `Россия · ${sl} ${al}` },
      { s: { region: 'moscow', sex, age: 'all' }, l: `Москва · ${sl}` },
      { s: { region: 'moscow', sex, age: band }, l: `Москва · ${sl} ${al}` },
      { s: { region: 'moscow', sex, age: '18-24', special: 'topuni' }, l: `Топ-вузы · ${sl}` },
    ];
    return list.map(x => ({ spec: Object.assign({ special: 'none' }, x.s), label: x.l }));
  }
  function renderComparison(cols, curKey) {
    const feats = M.features.filter(f => !f.descriptive && cols.some(c => c.fr.find(r => r.id === f.id && r.status === 'ok')));
    const cellP = p => p === null || p === undefined ? '<td class="txt">н/д</td>' : `<td style="background:${divColor(p)};color:${divText(p)}" data-tip="${esc(pctNum(p) + '-й перцентиль')}">${pctNum(p)}</td>`;
    let h = `<table class="heat"><thead><tr><th></th>${cols.map(c => `<th class="col${c.group.key === curKey ? ' cur' : ''}">${esc(c.label)}</th>`).join('')}</tr></thead><tbody>`;
    h += `<tr><td class="lbl"><b>Привлекательность</b></td>${cols.map(c => cellP(c.attr)).join('')}</tr>`;
    h += `<tr><td class="lbl"><b>Социальное положение</b></td>${cols.map(c => cellP(c.ses)).join('')}</tr>`;
    h += `<tr><td class="lbl">1 из N, с корреляциями</td>${cols.map(c => `<td class="txt">${c.rar ? big(1 / c.rar.honest) : '—'}</td>`).join('')}</tr>`;
    h += `<tr><td class="lbl">1 из N, наивно</td>${cols.map(c => `<td class="txt">${c.rar ? big(1 / c.rar.naive) : '—'}</td>`).join('')}</tr>`;
    h += `<tr class="sep"><td colspan="${cols.length + 1}"></td></tr>`;
    for (const f of feats) {
      h += `<tr><td class="lbl">${esc(f.short || f.label)}</td>${cols.map(c => { const r = c.fr.find(x => x.id === f.id); return cellP(r && r.status === 'ok' ? r.pct : null); }).join('')}</tr>`;
    }
    h += '</tbody></table>';
    $('#compare').innerHTML = h;
  }

  // ---------- статические блоки ----------
  function renderCorr() {
    const R = M.corrMatrix(1), F = M.COP;
    let h = `<table class="corr"><thead><tr><th></th>${F.map(f => `<th>${esc(f.short || f.label)}</th>`).join('')}</tr></thead><tbody>`;
    F.forEach((f, i) => {
      h += `<tr><th>${esc(f.short || f.label)}</th>${F.map((g, j) => {
        const r = R[i][j], p = 0.5 + r / 2;
        const shown = i === j ? '' : Math.abs(r) >= 0.095 ? nf(r * 10, 0) : '';
        return `<td style="background:${i === j ? 'var(--surface-2)' : divColor(p)};color:${divText(p)}" data-tip="${esc((f.short || f.label) + ' ↔ ' + (g.short || g.label) + ': r = ' + nf(r, 2))}">${shown}</td>`;
      }).join('')}</tr>`;
    });
    h += '</tbody></table><p class="explain">Числа в клетках — r×10. Наведи, чтобы увидеть точное значение. Корреляции действуют внутри ячейки пол×возраст; смешение полов и возрастов добавляет свои.</p>';
    $('#corr').innerHTML = h;
  }
  function renderSources() {
    $('#sources').innerHTML = Object.entries(D.sources).map(([id, s]) => `<li><span class="id">${esc(id)}</span> — ${esc(s.t)}${s.u ? ` <a href="${esc(s.u)}" target="_blank" rel="noopener">${esc(s.u.replace(/^https?:\/\//, '').slice(0, 60))}</a>` : ''}</li>`).join('');
  }

  // ---------- пересчёт ----------
  let timer = null;
  function update(immediate) {
    renderGroupBar();
    clearTimeout(timer);
    timer = setTimeout(recompute, immediate ? 0 : 280);
  }
  async function recompute() {
    const gen = ++state.gen;
    const stale = () => gen !== state.gen;
    const status = t => { $('#status').textContent = t; };
    const user = M.userFromProfile(state.profile);
    const spec = groupSpec();
    const group = M.buildGroup(spec);
    const sp = D.groups.special.find(s => s.id === spec.special);
    $('#group-info').innerHTML = `Группа: <b>${esc(group.label)}</b> · ≈ ${big(group.size)} человек${sp && sp.note && spec.special !== 'none' ? ' · ' + esc(sp.note) : ''}`;
    status('Считаю перцентили…');
    await tick(); if (stale()) return;
    const fr = M.featureResults(user, group);
    const fids = M.selectRarityFeatures(fr, state.mode, state.excluded, state.forced);
    renderFeatures(fr, group, fids);
    renderStrengths(fr);
    renderIndexPending('attr'); renderIndexPending('ses');
    status('Считаю «один из N»…');
    await tick(); if (stale()) return;
    const rar = fids.length ? M.rarity(user, group, fids) : null;
    renderRarity(rar, fids, group, fr);
    status('Считаю индекс привлекательности…');
    await tick(); if (stale()) return;
    renderIndex('attr', M.computeIndex('attr', user, group));
    status('Считаю индекс положения…');
    await tick(); if (stale()) return;
    renderIndex('ses', M.computeIndex('ses', user, group));
    status('Строю кривую накопления…');
    await tick(); if (stale()) return;
    renderCurve(fids.length ? M.rarityCurve(user, group, fids) : []);
    status('Оцениваю, что подтянуть…');
    await tick(); if (stale()) return;
    renderImprovements(M.improvements(user, group, fids, state.mode));
    // сравнение групп
    const cols = [];
    for (const c of comparisonSpecs()) {
      status(`Сравниваю группы (${cols.length + 1}/8)…`);
      await tick(); if (stale()) return;
      const g = M.buildGroup(c.spec);
      const frg = M.featureResults(user, g, { draws: 0 });
      const fg = M.selectRarityFeatures(frg, state.mode, state.excluded, state.forced);
      cols.push({
        label: c.label, group: g, fr: frg,
        rar: fg.length ? M.rarity(user, g, fg, { draws: 0, M: 2500 }) : null,
        attr: M.indexPoint('attr', user, g), ses: M.indexPoint('ses', user, g),
      });
      renderComparison(cols, group.key);
    }
    status('');
  }

  // ---------- события ----------
  function onFormChange() {
    const prevBand = userBand();
    state.profile = readForm();
    if (state.group.age && state.group.age === prevBand) state.group.age = null;
    save();
    update();
  }
  function setProfile(p, banner) {
    state.profile = Object.assign({ version: 1, sex: 'male', home: 'russia', values: {} }, p);
    writeForm(state.profile);
    state.profile = readForm();
    state.group = { region: null, sex: null, age: null, special: 'none' };
    state.excluded.clear(); state.forced.clear();
    const b = $('#banner');
    if (banner) { b.innerHTML = banner; b.hidden = false; } else b.hidden = true;
    save();
    update(true);
  }
  // Сохранение: в артефакте claude.ai — через capability «downloads» (обычные ссылки там не работают),
  // локально — через blob-ссылку. Если ни то, ни другое недоступно — показываем JSON для копирования.
  const downloadsP = (window.claude && typeof window.claude.use === 'function') ? window.claude.use('downloads').catch(() => null) : Promise.resolve(null);
  function showBanner(html) { const b = $('#banner'); b.innerHTML = html; b.hidden = false; return b; }
  function showJsonPanel(text, why) {
    const b = showBanner(`${esc(why)} Скопируй текст и сохрани его в файл <code>.json</code>; загрузить его можно кнопкой «Загрузить JSON».
      <textarea id="json-out" readonly></textarea><button type="button" class="btn" id="btn-copy">Скопировать</button><button type="button" class="btn btn-ghost" id="btn-close-json">Закрыть</button><span id="copy-msg" class="muted"></span>`);
    const ta = $('#json-out', b); ta.value = text;
    $('#btn-copy', b).addEventListener('click', () => {
      const done = () => { $('#copy-msg', b).textContent = ' Скопировано.'; };
      const fallback = () => { ta.focus(); ta.select(); $('#copy-msg', b).textContent = ' Текст выделен — нажми Ctrl/Cmd+C.'; };
      try { navigator.clipboard.writeText(text).then(done, fallback); } catch (e) { fallback(); }
    });
    $('#btn-close-json', b).addEventListener('click', () => { b.hidden = true; });
  }
  async function download() {
    const p = readForm();
    const text = JSON.stringify(p, null, 2);
    const name = (p.name || 'profile').replace(/[^\p{L}\p{N}_-]+/gu, '_').slice(0, 40);
    const filename = `where-am-i_${name}.json`;
    const dl = await downloadsP;
    if (dl) {
      try { await dl.save({ filename, data: text }); showBanner(`Профиль сохранён как <b>${esc(filename)}</b>.`); }
      catch (e) { if (!e || e.code !== 'declined') showJsonPanel(text, 'Сохранить файл не получилось.'); }
      return;
    }
    if (window.claude) { showJsonPanel(text, 'Здесь файл нельзя скачать напрямую.'); return; }
    const blob = new Blob([text], { type: 'application/json' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob); a.download = filename;
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 1000);
  }
  function initTips() {
    const tip = $('#tip');
    document.addEventListener('mouseover', e => {
      const t = e.target.closest && e.target.closest('[data-tip]');
      if (!t) { tip.hidden = true; return; }
      tip.textContent = t.getAttribute('data-tip'); tip.hidden = false;
    });
    document.addEventListener('mousemove', e => {
      if (tip.hidden) return;
      const w = tip.offsetWidth, h = tip.offsetHeight;
      let x = e.clientX + 14, y = e.clientY + 14;
      if (x + w > window.innerWidth - 8) x = e.clientX - w - 14;
      if (y + h > window.innerHeight - 8) y = e.clientY - h - 14;
      tip.style.left = x + 'px'; tip.style.top = y + 'px';
    });
  }

  function init() {
    buildForm();
    renderCorr(); renderSources(); initTips();
    $('#form').addEventListener('input', onFormChange);
    $('#form').addEventListener('change', onFormChange);
    $('#btn-example').addEventListener('click', () => setProfile(JSON.parse(JSON.stringify(D.exampleProfile)), 'Загружен <b>вымышленный</b> пример. Замени поля своими данными или загрузи свой JSON.'));
    $('#btn-clear').addEventListener('click', () => setProfile({ sex: 'male', age: '', home: 'russia', values: {} }));
    $('#btn-save').addEventListener('click', download);
    $('#file-load').addEventListener('change', e => {
      const file = e.target.files[0]; if (!file) return;
      const rd = new FileReader();
      rd.onload = () => {
        try { const pr = JSON.parse(rd.result); setProfile(pr, `Загружен профиль «${esc(pr.name || file.name)}».`); }
        catch (err) { showBanner(`Файл «${esc(file.name)}» не похож на профиль: ${esc(err.message)}. Нужен JSON, сохранённый этим приложением.`); }
        e.target.value = '';
      };
      rd.readAsText(file);
    });
    $('#chk-topuni').addEventListener('change', e => { state.group.special = e.target.checked ? 'topuni' : 'none'; update(); });
    $$('#seg-mode button').forEach(b => b.addEventListener('click', () => { state.mode = b.dataset.mode; state.forced.clear(); update(); }));
    $$('#seg-sort button').forEach(b => b.addEventListener('click', () => { state.sort = b.dataset.sort; renderGroupBar(); renderImprovements(state.lastImpr); }));
    const stored = loadStored();
    if (stored) setProfile(stored);
    else setProfile(JSON.parse(JSON.stringify(D.exampleProfile)), 'Это <b>вымышленный</b> пример, чтобы было что посмотреть. Заполни форму слева своими данными; профиль можно сохранить в JSON.');
  }
  init();
})();
