/* Статистические примитивы: нормальное распределение, ГПСЧ, линейная алгебра,
   многомерное нормальное с importance sampling для вероятностей «ортантов».
   Работает и в браузере (window.Stats), и в Node (module.exports). */
(function (root) {
  'use strict';

  // ---------- нормальное распределение ----------
  // erfc с относительной точностью ~1.2e-7 на всей оси (Numerical Recipes, erfcc) —
  // важно для хвостов: вероятности 1e-6 должны считаться с относительной, а не абсолютной ошибкой.
  function erfc(x) {
    const z = Math.abs(x);
    const t = 1 / (1 + 0.5 * z);
    const r = t * Math.exp(-z * z - 1.26551223 + t * (1.00002368 + t * (0.37409196 + t * (0.09678418 +
      t * (-0.18628806 + t * (0.27886807 + t * (-1.13520398 + t * (1.48851587 +
      t * (-0.82215223 + t * 0.17087277)))))))));
    return x >= 0 ? r : 2 - r;
  }
  function normCdf(x) {
    if (x === Infinity) return 1;
    if (x === -Infinity) return 0;
    return 0.5 * erfc(-x / Math.SQRT2);
  }
  function normPdf(x) { return Math.exp(-0.5 * x * x) / Math.sqrt(2 * Math.PI); }

  // Обратная функция Φ: алгоритм Acklam + один шаг Галлея (точность ~1e-15).
  function normInv(p) {
    if (p <= 0) return -Infinity;
    if (p >= 1) return Infinity;
    const a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02, 1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00];
    const b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02, 6.680131188771972e+01, -1.328068155288572e+01];
    const c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00, -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00];
    const d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00, 3.754408661907416e+00];
    const pl = 0.02425;
    let q, r, x;
    if (p < pl) {
      q = Math.sqrt(-2 * Math.log(p));
      x = (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1);
    } else if (p <= 1 - pl) {
      q = p - 0.5; r = q * q;
      x = (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q / (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1);
    } else {
      q = Math.sqrt(-2 * Math.log(1 - p));
      x = -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1);
    }
    // шаг Галлея
    const e = normCdf(x) - p;
    const u = e * Math.sqrt(2 * Math.PI) * Math.exp(x * x / 2);
    return x - u / (1 + x * u / 2);
  }

  // ---------- ГПСЧ с зерном (воспроизводимость и общие случайные числа) ----------
  function rng(seed) {
    let s = (seed >>> 0) || 1;
    let spare = null;
    const uniform = function () {
      s = (s + 0x6D2B79F5) >>> 0;
      let t = s;
      t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
    const normal = function () {
      if (spare !== null) { const v = spare; spare = null; return v; }
      let u, v, r;
      do { u = 2 * uniform() - 1; v = 2 * uniform() - 1; r = u * u + v * v; } while (r >= 1 || r === 0);
      const m = Math.sqrt(-2 * Math.log(r) / r);
      spare = v * m;
      return u * m;
    };
    return { uniform, normal };
  }

  // ---------- линейная алгебра ----------
  function identity(n) { const m = []; for (let i = 0; i < n; i++) { m.push(new Array(n).fill(0)); m[i][i] = 1; } return m; }

  // Собственные числа/векторы симметричной матрицы (метод Якоби).
  function jacobiEigen(A) {
    const n = A.length;
    const a = A.map(r => r.slice());
    const v = identity(n);
    for (let sweep = 0; sweep < 100; sweep++) {
      let off = 0;
      for (let i = 0; i < n; i++) for (let j = i + 1; j < n; j++) off += a[i][j] * a[i][j];
      if (off < 1e-20) break;
      for (let p = 0; p < n; p++) for (let q = p + 1; q < n; q++) {
        if (Math.abs(a[p][q]) < 1e-15) continue;
        const theta = (a[q][q] - a[p][p]) / (2 * a[p][q]);
        const t = Math.sign(theta || 1) / (Math.abs(theta) + Math.sqrt(theta * theta + 1));
        const c = 1 / Math.sqrt(t * t + 1), s = t * c;
        for (let k = 0; k < n; k++) {
          const akp = a[k][p], akq = a[k][q];
          a[k][p] = c * akp - s * akq; a[k][q] = s * akp + c * akq;
        }
        for (let k = 0; k < n; k++) {
          const apk = a[p][k], aqk = a[q][k];
          a[p][k] = c * apk - s * aqk; a[q][k] = s * apk + c * aqk;
        }
        for (let k = 0; k < n; k++) {
          const vkp = v[k][p], vkq = v[k][q];
          v[k][p] = c * vkp - s * vkq; v[k][q] = s * vkp + c * vkq;
        }
      }
    }
    return { values: a.map((r, i) => r[i]), vectors: v };
  }

  // Ближайшая (в смысле обрезки спектра) корреляционная матрица: литература даёт
  // попарные r из разных выборок, их набор не обязан быть положительно определённым.
  function nearestCorrelation(R, minEig) {
    minEig = minEig || 0.03;
    const n = R.length;
    const { values, vectors } = jacobiEigen(R);
    const lam = values.map(x => Math.max(x, minEig));
    const M = [];
    for (let i = 0; i < n; i++) {
      M.push(new Array(n).fill(0));
      for (let j = 0; j < n; j++) {
        let s = 0;
        for (let k = 0; k < n; k++) s += vectors[i][k] * lam[k] * vectors[j][k];
        M[i][j] = s;
      }
    }
    const d = M.map((r, i) => Math.sqrt(r[i]));
    for (let i = 0; i < n; i++) for (let j = 0; j < n; j++) M[i][j] /= d[i] * d[j];
    return M;
  }

  function cholesky(A) {
    const n = A.length;
    const L = [];
    for (let i = 0; i < n; i++) L.push(new Float64Array(n));
    for (let i = 0; i < n; i++) {
      for (let j = 0; j <= i; j++) {
        let s = A[i][j];
        for (let k = 0; k < j; k++) s -= L[i][k] * L[j][k];
        if (i === j) L[i][i] = Math.sqrt(Math.max(s, 1e-12));
        else L[i][j] = s / L[j][j];
      }
    }
    return L;
  }
  // решить L y = b
  function forwardSolve(L, b) {
    const n = b.length, y = new Float64Array(n);
    for (let i = 0; i < n; i++) { let s = b[i]; for (let k = 0; k < i; k++) s -= L[i][k] * y[k]; y[i] = s / L[i][i]; }
    return y;
  }
  // решить L^T x = y
  function backSolveT(L, y) {
    const n = y.length, x = new Float64Array(n);
    for (let i = n - 1; i >= 0; i--) { let s = y[i]; for (let k = i + 1; k < n; k++) s -= L[k][i] * x[k]; x[i] = s / L[i][i]; }
    return x;
  }
  function inverseFromCholesky(L) {
    const n = L.length, inv = [];
    for (let j = 0; j < n; j++) {
      const e = new Float64Array(n); e[j] = 1;
      const col = backSolveT(L, forwardSolve(L, e));
      for (let i = 0; i < n; i++) { if (!inv[i]) inv[i] = new Float64Array(n); inv[i][j] = col[i]; }
    }
    return inv;
  }
  function submatrix(R, idx) { return idx.map(i => idx.map(j => R[i][j])); }

  // ---------- P(Z >= t) для Z ~ N(0, R): алгоритм GHK / Genz ----------
  // Z = L e. Последовательно для i: e_i должно быть ≥ a_i = (t_i − Σ_{k<i} L_ik e_k)/L_ii.
  // Вес выборки = Π P(e_i ≥ a_i), e_i тянется из усечённой нормали. Несмещённая оценка с
  // малой дисперсией даже для хвостов ~1e-12 и 20+ измерений (Genz 1992; Genz & Bretz 2009).
  // Переменные переупорядочиваются: сначала самые «ограничивающие» (эвристика Genz–Bretz).
  function orthantProb(R, t, M, seed) {
    const d0 = t.length;
    if (d0 === 0) return { p: 1, se: 0 };
    if (d0 === 1) return { p: normCdf(-t[0]), se: 0 };
    // жадное переупорядочивание по ожидаемой условной вероятности (упрощённо — по t)
    const order = t.map((v, i) => i).sort((a, b) => t[b] - t[a]);
    const Rr = order.map(i => order.map(j => R[i][j]));
    const tt = order.map(i => t[i]);
    const L = cholesky(Rr);
    const d = d0;
    const r = rng(seed || 12345);
    const e = new Float64Array(d);
    let sum = 0, sum2 = 0;
    for (let m = 0; m < M; m++) {
      let w = 1;
      for (let i = 0; i < d; i++) {
        let s = tt[i];
        const Li = L[i];
        for (let k = 0; k < i; k++) s -= Li[k] * e[k];
        const a = s / Li[i];
        const q = normCdf(-a);            // P(e_i ≥ a), точно в хвосте
        w *= q;
        if (w < 1e-300) { w = 0; break; }
        if (i < d - 1) {
          const u = r.uniform();
          // e_i = Φ⁻¹(1 − u·q) = −Φ⁻¹(u·q): устойчиво при q → 0
          e[i] = -normInv(Math.max(u * q, 1e-300));
        }
      }
      sum += w; sum2 += w * w;
    }
    const p = sum / M;
    const se = Math.sqrt(Math.max(sum2 / M - p * p, 0) / M);
    return { p, se };
  }

  // Условное распределение части латентных переменных при известных остальных.
  // Возвращает {mean, sd} для каждой неизвестной (маргинально, по отдельности).
  function conditionalNormals(R, knownIdx, knownZ, unknownIdx) {
    if (knownIdx.length === 0) return unknownIdx.map(() => ({ mean: 0, sd: 1 }));
    const Roo = submatrix(R, knownIdx);
    const L = cholesky(Roo);
    const alpha = backSolveT(L, forwardSolve(L, Float64Array.from(knownZ)));
    return unknownIdx.map(u => {
      const r = knownIdx.map(k => R[u][k]);
      let mean = 0; for (let i = 0; i < r.length; i++) mean += r[i] * alpha[i];
      const y = forwardSolve(L, Float64Array.from(r));
      let v = 1; for (let i = 0; i < y.length; i++) v -= y[i] * y[i];
      return { mean, sd: Math.sqrt(Math.max(v, 0.02)) };
    });
  }

  function quantile(sortedArr, q) {
    if (!sortedArr.length) return NaN;
    const pos = (sortedArr.length - 1) * q;
    const lo = Math.floor(pos), hi = Math.ceil(pos);
    return sortedArr[lo] + (sortedArr[hi] - sortedArr[lo]) * (pos - lo);
  }
  // доля элементов отсортированного массива строго меньше x (+ половина равных)
  function rankIn(sortedArr, x) {
    let lo = 0, hi = sortedArr.length;
    while (lo < hi) { const m = (lo + hi) >> 1; if (sortedArr[m] < x) lo = m + 1; else hi = m; }
    let lo2 = lo, hi2 = sortedArr.length;
    while (lo2 < hi2) { const m = (lo2 + hi2) >> 1; if (sortedArr[m] <= x) lo2 = m + 1; else hi2 = m; }
    return (lo + 0.5 * (lo2 - lo)) / sortedArr.length;
  }
  function clamp(x, a, b) { return Math.min(b, Math.max(a, x)); }
  function interp(points, x) {
    if (x <= points[0][0]) return points[0][1];
    for (let i = 1; i < points.length; i++) {
      if (x <= points[i][0]) {
        const [x0, y0] = points[i - 1], [x1, y1] = points[i];
        return y0 + (y1 - y0) * (x - x0) / (x1 - x0);
      }
    }
    return points[points.length - 1][1];
  }

  const Stats = { erfc, normCdf, normPdf, normInv, rng, jacobiEigen, nearestCorrelation, cholesky,
    forwardSolve, backSolveT, inverseFromCholesky, submatrix, orthantProb, conditionalNormals,
    quantile, rankIn, clamp, interp };
  if (typeof module !== 'undefined' && module.exports) module.exports = Stats;
  else root.Stats = Stats;
})(typeof window !== 'undefined' ? window : globalThis);
