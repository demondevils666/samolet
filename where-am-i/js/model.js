/* Модель: из данных (data.js) и профиля считает перцентили, «один из N»
   (наивно и с корреляциями), индексы привлекательности и SES, эффекты улучшений.
   Без зависимостей от DOM — можно гонять в Node (см. test/run-tests.js). */
(function (root) {
  'use strict';
  const S = (typeof module !== 'undefined' && module.exports) ? require('./stats.js') : root.Stats;
  const { normCdf, normInv, rng, clamp, interp } = S;

  function createModel(DATA) {
    const F = DATA.features;
    const byId = Object.fromEntries(F.map(f => [f.id, f]));
    const COP = F.filter(f => !f.descriptive);           // признаки в копуле
    const copIndex = Object.fromEntries(COP.map((f, i) => [f.id, i]));
    const AGE_IDS = DATA.groups.ages.map(a => a.id);

    // ---------- корреляционная матрица ----------
    const baseR = COP.map((_, i) => COP.map((_, j) => (i === j ? 1 : 0)));
    for (const [a, b, r] of DATA.correlations) {
      if (!(a in copIndex) || !(b in copIndex)) continue;
      baseR[copIndex[a]][copIndex[b]] = r;
      baseR[copIndex[b]][copIndex[a]] = r;
    }
    const corrCache = new Map();
    function corrMatrix(scale) {
      scale = Math.round((scale || 1) * 100) / 100;
      if (corrCache.has(scale)) return corrCache.get(scale);
      const R = baseR.map((row, i) => row.map((v, j) => (i === j ? 1 : clamp(v * scale, -0.95, 0.95))));
      const fixed = S.nearestCorrelation(R, 0.03);
      corrCache.set(scale, fixed);
      return fixed;
    }

    // ---------- маргинальные распределения ----------
    function normProbs(p) { const s = p.reduce((a, b) => a + b, 0); return p.map(x => x / s); }
    function baseParams(f, region, sex) { const r = f.params && f.params[region]; return r ? (r[sex] || r.any || null) : null; }
    function ageShift(f, sex, age) {
      const a = f.ageShift; if (!a) return 0;
      const t = (a.male || a.female) ? (a[sex] || {}) : a;
      return t[age] || 0;
    }
    function applicable(f, cell) {
      if (f.applies) {
        if (f.applies.regions && !f.applies.regions.includes(cell.region)) return false;
        if (f.applies.ages && !f.applies.ages.includes(cell.age)) return false;
      }
      return !!baseParams(f, cell.region, cell.sex);
    }

    function makeMarginal(f, p, shift) {
      const sign = f.direction === 'lower' ? -1 : 1;
      if (f.type === 'normal') {
        const mean = p.mean + sign * shift * p.sd, sd = p.sd;
        const cdf = x => normCdf((x - mean) / sd);
        const q = u => mean + sd * normInv(u);
        return {
          type: 'normal', mean, sd, cdf,
          pdf: x => S.normPdf((x - mean) / sd) / sd,
          worse(x) { const c = cdf(x); const v = sign > 0 ? c : 1 - c; return { lo: v, hi: v }; },
          fromBetterU(u) { return sign > 0 ? q(u) : q(1 - u); },
          quantile: q,
        };
      }
      if (f.type === 'lognormal') {
        const mu = Math.log(p.median) + sign * shift * p.sigma, sg = p.sigma;
        const p0 = p.zeroMass ? normCdf(normInv(p.zeroMass) - sign * shift) : 0;
        const cdfPos = y => (y <= 0 ? p0 : p0 + (1 - p0) * normCdf((Math.log(y) - mu) / sg));
        const q = u => {
          if (u < p0) return 0;
          const v = Math.exp(mu + sg * normInv(clamp((u - p0) / (1 - p0), 1e-12, 1 - 1e-12)));
          return f.discrete ? Math.round(v) : v;
        };
        return {
          type: 'lognormal', mu, sigma: sg, p0, cdf: cdfPos, median: Math.exp(mu),
          pdf: x => (x <= 0 ? 0 : (1 - p0) * S.normPdf((Math.log(x) - mu) / sg) / (sg * x)),
          worse(x) {
            if (f.discrete) {
              if (x <= 0) return { lo: 0, hi: cdfPos(0.5) };
              return { lo: cdfPos(x - 0.5), hi: cdfPos(x + 0.5) };
            }
            if (x <= 0) return { lo: 0, hi: p0 };
            const c = cdfPos(x); return { lo: c, hi: c };
          },
          fromBetterU: q, quantile: q,
        };
      }
      if (f.type === 'categorical') {
        let probs = normProbs(p.probs);
        if (shift) {
          let cum = 0; const C = [];
          for (let k = 0; k < probs.length - 1; k++) { cum += probs[k]; C.push(normCdf(normInv(clamp(cum, 1e-12, 1 - 1e-12)) - shift)); }
          const np = []; let prev = 0;
          for (let k = 0; k < probs.length - 1; k++) { np.push(Math.max(C[k] - prev, 0)); prev = C[k]; }
          np.push(Math.max(1 - prev, 0));
          probs = normProbs(np);
        }
        const cumBefore = []; let c = 0;
        for (const pr of probs) { cumBefore.push(c); c += pr; }
        return {
          type: 'categorical', probs,
          worse(k) { return { lo: cumBefore[k], hi: cumBefore[k] + probs[k] }; },
          fromBetterU(u) { for (let k = 0; k < probs.length; k++) if (u < cumBefore[k] + probs[k]) return k; return probs.length - 1; },
        };
      }
      throw new Error('unknown type ' + f.type);
    }

    const margCache = new Map();
    function marginal(f, cell, extraShift) {
      extraShift = extraShift || 0;
      const key = f.id + '|' + cell.region + '|' + cell.sex + '|' + cell.age + '|' + cell.special;
      if (!extraShift && margCache.has(key)) return margCache.get(key);
      let m = null;
      if (applicable(f, cell)) {
        let p = baseParams(f, cell.region, cell.sex), shift = 0;
        const ov = f.overrides && (f.overrides[cell.region + '|' + cell.sex + '|' + cell.age] || f.overrides[cell.region + '|any|' + cell.age]);
        if (ov) p = ov; else shift += ageShift(f, cell.sex, cell.age);
        const sp = cell.special && cell.special !== 'none' && f.special && f.special[cell.special];
        if (sp) {
          if (sp.params) { p = sp.params[cell.sex] || sp.params.any; shift = 0; }
          else shift += sp.shift || 0;
        }
        m = makeMarginal(f, p, shift + extraShift);
      }
      if (!extraShift) margCache.set(key, m);
      return m;
    }

    // ---------- группы ----------
    function buildGroup(spec) {
      let { region, sex, age, special } = Object.assign({ region: 'russia', sex: 'male', age: 'all', special: 'none' }, spec);
      if (special === 'topuni') { region = 'moscow'; age = '18-24'; }
      const sexes = sex === 'all' ? ['male', 'female'] : [sex];
      const ages = age === 'all' ? AGE_IDS : [age];
      const aw = DATA.groups.ageWeights[region];
      const cells = [];
      for (const s of sexes) for (const a of ages) cells.push({ region, sex: s, age: a, special, w: (1 / sexes.length) * (age === 'all' ? aw[a] : 1) });
      const tw = cells.reduce((x, c) => x + c.w, 0);
      cells.forEach(c => { c.w /= tw; });
      const lbl = (arr, id) => (arr.find(x => x.id === id) || {}).label || id;
      const label = special === 'topuni'
        ? 'Студенты топ-вузов · ' + lbl(DATA.groups.sexes, sex).toLowerCase()
        : [lbl(DATA.groups.regions, region), lbl(DATA.groups.sexes, sex).toLowerCase(), age === 'all' ? '18–64' : lbl(DATA.groups.ages, age)].join(' · ');
      const size = DATA.groups.popSize[special === 'topuni' ? 'topuni' : region] * (sex === 'all' ? 1 : 0.5) * (age === 'all' || special === 'topuni' ? 1 : aw[age]);
      return { region, sex, age, special, cells, label, size, key: [region, sex, age, special].join('|') };
    }

    function reliabilityOf(f, group) {
      let r = (f.reliability && f.reliability[group.region]) || 'rough';
      if (group.special === 'topuni' && r !== 'na') r = 'rough';
      return r;
    }

    // взвешенная по ячейкам доля «хуже» / «хуже или так же»
    function groupWorse(f, group, x, shift) {
      let lo = 0, hi = 0, w = 0;
      for (const c of group.cells) {
        const m = marginal(f, c, shift);
        if (!m) continue;
        const r = m.worse(x); lo += c.w * r.lo; hi += c.w * r.hi; w += c.w;
      }
      if (!w) return null;
      return { lo: lo / w, hi: hi / w, cover: w };
    }

    // ---------- профиль → наблюдения ----------
    function ageBand(age) {
      for (const a of DATA.groups.ages) if (age >= a.range[0] && age <= a.range[1]) return a.id;
      return age < 18 ? '18-24' : '55-64';
    }
    function num(v) { if (v === '' || v === null || v === undefined) return null; const n = Number(v); return Number.isFinite(n) ? n : null; }
    function methodOpt(f, values) {
      if (!f.method) return null;
      const id = values[f.method.key] || f.method.default;
      return f.method.options.find(o => o.id === id) || f.method.options.find(o => o.id === f.method.default);
    }
    function vo2FromRun(minutes, meters) {
      meters = meters || 5000;
      const t = minutes, v = meters / t;
      const vo2 = -4.60 + 0.182258 * v + 0.000104 * v * v;
      const pct = 0.8 + 0.1894393 * Math.exp(-0.012778 * t) + 0.2989558 * Math.exp(-0.1932605 * t);
      return vo2 / pct;
    }

    function userFromProfile(profile) {
      const v = (profile && profile.values) || {};
      const sex = profile && profile.sex === 'female' ? 'female' : 'male';
      const age = num(profile && profile.age) || 30;
      const obs = {};
      const set = (id, x, noise, extra) => { obs[id] = Object.assign({ x, noise: noise || {} }, extra || {}); };
      const h = num(v.height), w = num(v.weight);
      if (h) set('height', h, { sd: 1 });
      let bmi = null;
      if (h && w) { bmi = w / Math.pow(h / 100, 2); set('bmi', bmi, { logSd: 0.01 }); }
      const bf = num(v.bodyfat);
      if (bf !== null) { const o = methodOpt(byId.bodyfat, v); set('bodyfat', bf + o.bias, { sd: o.sd }, { method: o.label, adjusted: o.bias !== 0 ? o.bias : 0 }); }
      else if (bmi) { set('bodyfat', 1.2 * bmi + 0.23 * age - 10.8 * (sex === 'male' ? 1 : 0) - 5.4, { sd: 5 }, { estimated: 'оценка по ИМТ и возрасту (Deurenberg)' }); }
      for (const id of ['bench', 'squat']) {
        const kg = num(v[id]);
        if (kg !== null && w) set(id, kg / w, byId[id].noise, { rawKg: kg });
      }
      const vo2 = num(v.vo2), run = num(v.run5k);
      if (vo2 !== null) { const o = methodOpt(byId.vo2, Object.assign({}, v, { vo2Method: v.vo2Method === 'run' ? 'watch' : v.vo2Method })); set('vo2', vo2 + o.bias, { sd: o.sd }, { method: o.label }); }
      else if (run !== null) { set('vo2', vo2FromRun(run), { sd: 3 }, { estimated: 'из времени на 5 км (Daniels–Gilbert)' }); }
      const face = num(v.face);
      if (face !== null) { const o = methodOpt(byId.face, v); set('face', clamp(face + o.bias, 1, 10), { sd: o.sd }, { method: o.label, adjusted: o.bias }); }
      const iq = num(v.iq);
      if (iq !== null) { const o = methodOpt(byId.iq, v); set('iq', iq + o.bias, { sd: o.sd }, { method: o.label, adjusted: o.bias }); }
      for (const f of F) {
        if (obs[f.id] || f.derived) continue;
        if (['height', 'bodyfat', 'bench', 'squat', 'vo2', 'face', 'iq'].includes(f.id)) continue;
        if (f.type === 'categorical') {
          const k = f.categories.findIndex(c => c.id === v[f.id]);
          if (k >= 0) set(f.id, k, {});
        } else {
          const x = num(v[f.id]);
          if (x !== null) set(f.id, x, f.noise || {});
        }
      }
      return { sex, age, band: ageBand(age), obs, home: (profile && profile.home) || 'russia' };
    }

    function noisy(o, r) {
      const n = o.noise || {};
      let x = o.x;
      if (n.sd) x += n.sd * r.normal();
      if (n.logSd && x > 0) x *= Math.exp(n.logSd * r.normal());
      return x;
    }

    // ---------- перцентили по признакам ----------
    function featureResults(user, group, opts) {
      opts = opts || {};
      const draws = opts.draws === undefined ? 200 : opts.draws;
      return F.map((f, fi) => {
        const rel = reliabilityOf(f, group);
        const o = user.obs[f.id];
        const base = { id: f.id, f, reliability: rel };
        if (!group.cells.some(c => applicable(f, c))) return Object.assign(base, { status: 'na' });
        if (!o) return Object.assign(base, { status: 'missing' });
        const g = groupWorse(f, group, o.x);
        const r = rng(9001 + fi * 7919);
        const zsd = DATA.reliability[rel].zSD;
        const sims = [];
        for (let k = 0; k < draws; k++) {
          const x = f.type === 'categorical' ? o.x : noisy(o, r);
          const gg = groupWorse(f, group, x, zsd * r.normal());
          sims.push((gg.lo + gg.hi) / 2);
        }
        sims.sort((a, b) => a - b);
        return Object.assign(base, {
          status: 'ok', obs: o, x: o.x, lo: g.lo, hi: g.hi, pct: (g.lo + g.hi) / 2,
          ci: draws ? [S.quantile(sims, 0.1), S.quantile(sims, 0.9)] : null, pAtLeast: 1 - g.lo,
        });
      });
    }

    // ---------- «один из N» ----------
    // P(не хуже тебя по всем признакам из fids). Наивно: произведение маргинальных долей.
    // Честно: для каждой ячейки (пол×возраст) — гауссова копула + importance sampling, затем смесь.
    function rarityCore(user, group, fids, o) {
      const R = corrMatrix(o.corrScale || 1);
      const shifts = o.shifts || {};
      const xs = o.xs || {};
      let naive = 1;
      const perFeature = [];
      for (const id of fids) {
        const f = byId[id];
        let P = 0;
        for (const c of group.cells) {
          const m = marginal(f, c, shifts[id] || 0);
          P += c.w * (m ? 1 - m.worse(xs[id] !== undefined ? xs[id] : user.obs[id].x).lo : 1);
        }
        naive *= P;
        perFeature.push({ id, P });
      }
      let honest = 0, se2 = 0;
      group.cells.forEach((c, ci) => {
        const idx = [], t = [];
        for (const id of fids) {
          const m = marginal(byId[id], c, shifts[id] || 0);
          if (!m) continue;
          const lo = m.worse(xs[id] !== undefined ? xs[id] : user.obs[id].x).lo;
          if (lo <= 1e-12) continue;
          idx.push(copIndex[id]); t.push(normInv(Math.min(lo, 1 - 1e-15)));
        }
        // ячейкам с малым весом достаточно меньше выборок (дисперсия смеси ~ Σ w²·var)
        const Mc = Math.max(600, Math.round((o.M || 8000) * Math.sqrt(c.w)));
        const res = S.orthantProb(S.submatrix(R, idx), t, Mc, (o.seed || 1) + ci * 104729);
        honest += c.w * res.p; se2 += c.w * c.w * res.se * res.se;
      });
      return { naive, honest, honestSE: Math.sqrt(se2), perFeature };
    }

    function rarity(user, group, fids, opts) {
      opts = opts || {};
      const point = rarityCore(user, group, fids, { M: opts.M || 8000, seed: opts.seed || 7 });
      const draws = opts.draws === undefined ? 20 : opts.draws;
      const r = rng(424242);
      const lnN = [], lhN = [];
      for (let k = 0; k < draws; k++) {
        const shifts = {}, xs = {};
        for (const id of fids) {
          const f = byId[id];
          shifts[id] = DATA.reliability[reliabilityOf(f, group)].zSD * r.normal();
          xs[id] = f.type === 'categorical' ? user.obs[id].x : noisy(user.obs[id], r);
        }
        const corrScale = 0.75 + 0.5 * r.uniform();
        const res = rarityCore(user, group, fids, { M: opts.drawM || 1500, seed: 1000 + k * 31, shifts, xs, corrScale });
        lnN.push(-Math.log10(Math.max(res.naive, 1e-300)));
        lhN.push(-Math.log10(Math.max(res.honest, 1e-300)));
      }
      lnN.sort((a, b) => a - b); lhN.sort((a, b) => a - b);
      return Object.assign(point, {
        log10Naive: -Math.log10(point.naive), log10Honest: -Math.log10(point.honest),
        naiveCI: draws ? [S.quantile(lnN, 0.1), S.quantile(lnN, 0.9)] : null,
        honestCI: draws ? [S.quantile(lhN, 0.1), S.quantile(lhN, 0.9)] : null,
      });
    }

    // накопление: признаки по возрастанию маргинальной доли
    function rarityCurve(user, group, fids, opts) {
      opts = opts || {};
      const P = fids.map(id => ({ id, P: rarityCore(user, group, [id], { M: 1 }).naive }));
      P.sort((a, b) => a.P - b.P);
      const out = [];
      for (let k = 1; k <= P.length; k++) {
        const sub = P.slice(0, k).map(p => p.id);
        const res = rarityCore(user, group, sub, { M: opts.M || 2000, seed: 77 });
        out.push({ id: P[k - 1].id, P: P[k - 1].P, naive: res.naive, honest: res.honest });
      }
      return out;
    }

    // ---------- синтетическая популяция для индексов ----------
    const popCache = new Map();
    const POP_N = 6000;
    function latentMid(f, group, x, shift) {
      const g = groupWorse(f, group, x, shift);
      if (!g) return NaN;
      return clamp(normInv(clamp((g.lo + g.hi) / 2, 1e-9, 1 - 1e-9)), -3.7, 3.7);
    }
    function simulatePopulation(group, N, seed) {
      const key = group.key + '|' + N + '|' + seed;
      if (popCache.has(key)) return popCache.get(key);
      const R = corrMatrix(1), L = S.cholesky(R), d = COP.length;
      const r = rng(seed);
      const people = [];
      const e = new Float64Array(d);
      group.cells.forEach((c, ci) => {
        const n = Math.max(1, Math.round(N * c.w));
        const margs = COP.map(f => marginal(f, c));
        for (let p = 0; p < n; p++) {
          for (let i = 0; i < d; i++) e[i] = r.normal();
          const raw = new Float64Array(d);
          for (let i = 0; i < d; i++) {
            let z = 0; for (let k = 0; k <= i; k++) z += L[i][k] * e[k];
            raw[i] = margs[i] ? margs[i].fromBetterU(normCdf(z)) : NaN;
          }
          people.push({ cell: ci, raw });
        }
      });
      // латентные «серединные» z относительно всей группы (нужны индексам)
      const gzCache = COP.map(() => new Map());
      for (const p of people) {
        p.gz = new Float64Array(d);
        for (let i = 0; i < d; i++) {
          const x = p.raw[i];
          if (Number.isNaN(x)) { p.gz[i] = NaN; continue; }
          const k = COP[i].type === 'categorical' || COP[i].discrete ? x : Math.round(x * 1000) / 1000;
          let z = gzCache[i].get(k);
          if (z === undefined) { z = latentMid(COP[i], group, x); gzCache[i].set(k, z); }
          p.gz[i] = z;
        }
      }
      const pop = { group, people };
      popCache.set(key, pop);
      return pop;
    }

    // ---------- индексы ----------
    const A = DATA.attractiveness, SES = DATA.ses;
    const PEN = A.penalties.map(p => ({ i: copIndex[p.feature], k: byId[p.feature].categories.findIndex(c => c.id === p.category), value: p.value }));
    function heightOffset(group) {
      // кривая роста задана для России; для других групп сдвигаем на разницу средних мужчин
      const m = marginal(byId.height, { region: group.region, sex: 'male', age: '25-34', special: 'none' });
      return m ? m.mean - A.components.find(c => c.id === 'height').anchorMean : 0;
    }
    function attrComponents(raw, gz, prm) {
      const out = {};
      for (const c of A.components) {
        let s = 0;
        if (c.kind === 'latent') s = gz[copIndex[c.feature]];
        else if (c.kind === 'curve') s = prm.curveScale * interp(c.curve, raw[copIndex.height] - prm.hOff);
        else if (c.kind === 'body') {
          const fat = interp(c.fatCurve, raw[copIndex.bodyfat]);
          let b = raw[copIndex.bench];
          if (Number.isNaN(b)) b = raw[copIndex.squat] * c.squatToBench;
          const mus = interp(c.muscleCurve, b);
          s = prm.curveScale * (c.fatShare * fat + (1 - c.fatShare) * mus);
        } else if (c.kind === 'mix') {
          let v = 0; for (const [id, w] of c.parts) v += w * gz[copIndex[id]];
          s = c.saturate * Math.tanh(v / c.saturate);
        }
        out[c.id] = s;
      }
      let pen = 0;
      for (const p of PEN) if (raw[p.i] === p.k) pen += p.value * prm.penaltyScale;
      out.penalty = pen;
      return out;
    }
    function attrTotal(comp, prm) { let u = comp.penalty; for (const c of A.components) u += prm.w[c.id] * comp[c.id]; return u; }
    function sesComponents(raw, gz) {
      const out = {};
      for (const c of SES.components) out[c.feature] = gz[copIndex[c.feature]];
      return out;
    }
    function sesTotal(comp, prm) {
      let u = 0; for (const c of SES.components) u += prm.w[c.feature] * comp[c.feature];
      return SES.saturate * Math.tanh(u / SES.saturate);
    }
    function baseParamsIdx(kind, group) {
      const w = {};
      if (kind === 'attr') { A.components.forEach(c => { w[c.id] = c.weight; }); return { w, curveScale: 1, penaltyScale: 1, hOff: heightOffset(group) }; }
      SES.components.forEach(c => { w[c.feature] = c.weight; });
      return { w };
    }
    function perturbParams(kind, base, r) {
      const spec = kind === 'attr' ? A : SES;
      const w = {}; let tot = 0, tot0 = 0;
      for (const k in base.w) { w[k] = base.w[k] * Math.exp(spec.weightUncertainty * r.normal()); tot += w[k]; tot0 += base.w[k]; }
      for (const k in w) w[k] *= tot0 / tot;
      const out = Object.assign({}, base, { w });
      if (kind === 'attr') {
        out.curveScale = Math.max(0.3, 1 + A.curveUncertainty * r.normal());
        out.penaltyScale = Math.max(0, 1 + A.penaltyUncertainty * r.normal());
      }
      return out;
    }
    function indexFeatures(kind) {
      if (kind === 'attr') {
        const s = new Set();
        for (const c of A.components) {
          if (c.feature) s.add(c.feature);
          if (c.kind === 'body') { s.add('bodyfat'); s.add('bench'); s.add('squat'); }
          if (c.parts) c.parts.forEach(p => s.add(p[0]));
        }
        A.penalties.forEach(p => s.add(p.feature));
        return [...s];
      }
      return SES.components.map(c => c.feature);
    }
    function refCell(group, user, forceSex) {
      const sex = forceSex || user.sex;
      return group.cells.find(c => c.sex === sex && c.age === user.band)
        || group.cells.filter(c => c.sex === sex).sort((a, b) => b.w - a.w)[0] || group.cells[0];
    }

    // Профиль пользователя для индекса: наблюдаемые значения + условная импутация пропусков.
    function userIndexVectors(user, group, kind, r, prm) {
      const d = COP.length;
      const cell = refCell(group, user, kind === 'attr' ? 'male' : null);
      let need = indexFeatures(kind);
      // если известен жим или присед — второй не импутируем (тело считается по любому из них)
      if (user.obs.bench || user.obs.squat) need = need.filter(id => id !== 'bench' && id !== 'squat');
      const raw = new Float64Array(d).fill(NaN), gz = new Float64Array(d).fill(NaN);
      const knownIdx = [], knownZ = [], unknown = [];
      for (let i = 0; i < d; i++) {
        const f = COP[i], o = user.obs[f.id];
        const m = marginal(f, cell);
        if (!m) continue;
        if (o) {
          let x = o.x;
          if (r && f.type !== 'categorical') x = noisy(o, r);
          const w = m.worse(x);
          let zc = normInv(clamp((w.lo + w.hi) / 2, 1e-9, 1 - 1e-9));
          let sh = 0;
          if (r) { sh = DATA.reliability[reliabilityOf(f, group)].zSD * r.normal(); }
          if (sh && f.type !== 'categorical') { x = m.fromBetterU(normCdf(zc - sh)); zc -= sh; }
          raw[i] = x; gz[i] = latentMid(f, group, x) - (f.type === 'categorical' ? sh : 0);
          knownIdx.push(i); knownZ.push(clamp(zc, -3.7, 3.7));
        } else if (need.includes(f.id)) unknown.push(i);
      }
      const missing = [];
      if (unknown.length) {
        const cond = S.conditionalNormals(corrMatrix(1), knownIdx, knownZ, unknown);
        unknown.forEach((i, k) => {
          const f = COP[i], m = marginal(f, cell);
          const z = cond[k].mean + (r ? cond[k].sd * r.normal() : 0);
          const x = m.fromBetterU(normCdf(z));
          raw[i] = x; gz[i] = latentMid(f, group, x);
          missing.push(f.id);
        });
      }
      return { raw, gz, missing };
    }

    function computeIndex(kind, user, group, opts) {
      opts = opts || {};
      const g = kind === 'attr' ? buildGroup({ region: group.region, sex: 'male', age: group.age, special: group.special }) : group;
      const pop = simulatePopulation(g, opts.N || POP_N, 2024);
      const base = baseParamsIdx(kind, g);
      const compFn = kind === 'attr' ? attrComponents : sesComponents;
      const totFn = kind === 'attr' ? attrTotal : sesTotal;
      const popComp = pop.people.map(p => compFn(p.raw, p.gz, base));
      // точечная оценка
      const uv = userIndexVectors(user, g, kind, null, base);
      const userComp = compFn(uv.raw, uv.gz, base);
      const popU = popComp.map(c => totFn(c, base)).sort((a, b) => a - b);
      const pointPct = S.rankIn(popU, totFn(userComp, base));
      // неопределённость
      const draws = opts.draws || 30;
      const r = rng(31337);
      const pcts = [];
      for (let k = 0; k < draws; k++) {
        const prm = perturbParams(kind, base, r);
        const pc = kind === 'attr' ? pop.people.map(p => attrComponents(p.raw, p.gz, prm)) : popComp;
        const pu = pc.map(c => totFn(c, prm)).sort((a, b) => a - b);
        const u = userIndexVectors(user, g, kind, r, prm);
        pcts.push(S.rankIn(pu, totFn(compFn(u.raw, u.gz, prm), prm)));
      }
      pcts.sort((a, b) => a - b);
      const ci = [S.quantile(pcts, 0.1), S.quantile(pcts, 0.9)];
      // вклад компонент относительно медианного человека популяции
      const keys = kind === 'attr' ? A.components.map(c => c.id).concat(['penalty']) : SES.components.map(c => c.feature);
      // вклад в п.п. перцентиля: насколько упадёт/вырастет место, если эту компоненту сделать медианной
      const contributions = keys.map(k => {
        const vals = popComp.map(c => c[k]).sort((a, b) => a - b);
        const med = S.quantile(vals, 0.5);
        const w = k === 'penalty' ? 1 : base.w[k];
        const spec = kind === 'attr' ? (A.components.find(c => c.id === k) || { label: 'Штрафы (курение, алкоголь)', short: 'Штрафы' }) : SES.components.find(c => c.feature === k);
        const alt = Object.assign({}, userComp, { [k]: med });
        const dp = pointPct - S.rankIn(popU, totFn(alt, base));
        return { id: k, label: spec.label, short: spec.short || spec.label, weight: w, user: userComp[k], median: med, contrib: w * (userComp[k] - med), dPct: dp };
      });
      const width = ci[1] - ci[0];
      const conf = width < 0.15 ? 'высокая' : width < 0.3 ? 'средняя' : 'низкая';
      const res = { kind, group: g, pct: pointPct, ci, conf, contributions, missing: uv.missing };
      if (kind === 'attr') {
        const mult = pp => Math.exp(A.attentionSigma * normInv(clamp(pp, 0.001, 0.999)));
        res.attention = { point: mult(pointPct), ci: [mult(ci[0]), mult(ci[1])] };
      }
      return res;
    }

    function indexPoint(kind, user, group) {
      const g = kind === 'attr' ? buildGroup({ region: group.region, sex: 'male', age: group.age, special: group.special }) : group;
      const pop = simulatePopulation(g, POP_N, 2024);
      const base = baseParamsIdx(kind, g);
      const compFn = kind === 'attr' ? attrComponents : sesComponents;
      const totFn = kind === 'attr' ? attrTotal : sesTotal;
      const key = 'U|' + kind + '|' + g.key;
      if (!pop[key]) pop[key] = pop.people.map(p => totFn(compFn(p.raw, p.gz, base), base)).sort((a, b) => a - b);
      const uv = userIndexVectors(user, g, kind, null, base);
      return S.rankIn(pop[key], totFn(compFn(uv.raw, uv.gz, base), base));
    }

    // ---------- что подтянуть ----------
    function applyImprovement(user, f) {
      const o = user.obs[f.id], im = f.improve;
      if (!o || !im) return null;
      let x = o.x;
      if (im.delta !== undefined) x = o.x + im.delta;
      if (im.factor !== undefined) x = o.x * im.factor;
      if (f.id === 'bodyfat') x = Math.max(x, 7);
      if (im.steps) x = Math.min(o.x + im.steps, f.categories.length - 1);
      if (im.toCategory) x = Math.max(o.x, f.categories.findIndex(c => c.id === im.toCategory));
      if (f.discrete) x = Math.round(x);
      if (x === o.x) return null;
      const obs = Object.assign({}, user.obs, { [f.id]: Object.assign({}, o, { x }) });
      return Object.assign({}, user, { obs });
    }
    function improvements(user, group, fids, mode) {
      const baseAttr = indexPoint('attr', user, group);
      const baseSes = indexPoint('ses', user, group);
      const baseN = fids.length ? rarityCore(user, group, fids, { M: 2500, seed: 5 }).honest : 1;
      const out = [];
      for (const f of COP) {
        const u2 = applyImprovement(user, f);
        if (!u2) continue;
        let set = fids.slice();
        if (!set.includes(f.id) && mode === 'strengths') {
          const g = groupWorse(f, group, u2.obs[f.id].x);
          if (g && (g.lo + g.hi) / 2 >= 0.5) set.push(f.id);
        }
        const n2 = set.length ? rarityCore(u2, group, set, { M: 2500, seed: 5 }).honest : 1;
        const g1 = groupWorse(f, group, user.obs[f.id].x), g2 = groupWorse(f, group, u2.obs[f.id].x);
        out.push({
          id: f.id, f, label: f.improve.label, effort: f.improve.effort,
          dPct: g1 && g2 ? (g2.lo + g2.hi) / 2 - (g1.lo + g1.hi) / 2 : 0,
          dAttr: indexPoint('attr', u2, group) - baseAttr,
          dSes: indexPoint('ses', u2, group) - baseSes,
          dLogN: Math.log10(baseN) - Math.log10(Math.max(n2, 1e-300)),
        });
      }
      return out;
    }

    function selectRarityFeatures(results, mode, excluded, forced) {
      excluded = excluded || new Set(); forced = forced || new Set();
      return results.filter(r => r.status === 'ok' && !r.f.descriptive && !excluded.has(r.id) && (mode === 'all' || r.pct >= 0.5 || forced.has(r.id))).map(r => r.id);
    }

    return {
      DATA, features: F, byId, COP, copIndex, corrMatrix, baseR, marginal, buildGroup, groupWorse, applicable, reliabilityOf,
      userFromProfile, ageBand, vo2FromRun, featureResults, rarity, rarityCore, rarityCurve, computeIndex, indexPoint,
      improvements, selectRarityFeatures, simulatePopulation,
    };
  }

  if (typeof module !== 'undefined' && module.exports) module.exports = { createModel };
  else root.createModel = createModel;
})(typeof window !== 'undefined' ? window : globalThis);
