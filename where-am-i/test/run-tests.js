/* Быстрые проверки математики: node test/run-tests.js */
const S = require('../js/stats.js');
const DATA = require('../js/data.js');
const { createModel } = require('../js/model.js');
const M = createModel(DATA);
let fails = 0;
function check(name, cond, info) { console.log((cond ? 'ok   ' : 'FAIL ') + name + (info !== undefined ? '  → ' + info : '')); if (!cond) fails++; }
const approx = (a, b, tol) => Math.abs(a - b) <= tol;

// 1. нормальное распределение
check('Φ(1.96)', approx(S.normCdf(1.96), 0.9750021048517795, 2e-7), S.normCdf(1.96));
check('Φ(-5) относит. точность', approx(S.normCdf(-5) / 2.866515718791939e-7, 1, 1e-5), S.normCdf(-5));
check('Φ⁻¹(Φ(x))', approx(S.normInv(S.normCdf(-3.3)), -3.3, 1e-8));

// 2. ортант: независимые → произведение; r=1-предел; известное значение для 2D
const I3 = [[1,0,0],[0,1,0],[0,0,1]];
const p3 = S.orthantProb(I3, [1, 1.5, 2], 40000, 3).p;
const ex3 = (1 - S.normCdf(1)) * (1 - S.normCdf(1.5)) * (1 - S.normCdf(2));
check('ортант независимый 3D', approx(p3 / ex3, 1, 0.03), p3.toExponential(3) + ' vs ' + ex3.toExponential(3));
// P(Z1>0,Z2>0) = 1/4 + asin(r)/(2π)
const r = 0.6, p2 = S.orthantProb([[1, r], [r, 1]], [0, 0], 40000, 5).p;
check('ортант 2D r=0.6 при t=0', approx(p2, 0.25 + Math.asin(r) / (2 * Math.PI), 0.005), p2.toFixed(4));
// хвост 10D, эквикорреляция 0.5, порог 2: сравнить с прямым МК на 2e6
{
  const d = 6, R = Array.from({ length: d }, (_, i) => Array.from({ length: d }, (_, j) => (i === j ? 1 : 0.5)));
  const t = new Array(d).fill(1.5);
  const is = S.orthantProb(R, t, 40000, 11).p;
  const L = S.cholesky(R), g = S.rng(99); let hit = 0; const n = 1e6;
  for (let k = 0; k < n; k++) { const e = Array.from({ length: d }, () => g.normal()); let ok = true; for (let i = 0; i < d && ok; i++) { let x = 0; for (let j = 0; j <= i; j++) x += L[i][j] * e[j]; if (x < t[i]) ok = false; } if (ok) hit++; }
  check('ортант 6D ρ=.5 GHK ≈ прямой МК', approx(is / (hit / n), 1, 0.06), is.toExponential(3) + ' vs ' + (hit / n).toExponential(3));
}

// 3. корреляционная матрица PD
const R = M.corrMatrix(1), ev = S.jacobiEigen(R).values;
check('матрица корреляций PD', Math.min(...ev) > 0.02, 'λmin=' + Math.min(...ev).toFixed(3));
let maxDiff = 0; for (let i = 0; i < R.length; i++) for (let j = 0; j < R.length; j++) maxDiff = Math.max(maxDiff, Math.abs(R[i][j] - M.baseR[i][j]));
check('PSD-поправка небольшая', maxDiff < 0.15, 'max|Δr|=' + maxDiff.toFixed(3));

// 4. маргинальные распределения: здравый смысл
const g = M.buildGroup({ region: 'russia', sex: 'male', age: '25-34' });
const pct = (id, x) => { const w = M.groupWorse(M.byId[id], g, x); return (w.lo + w.hi) / 2; };
check('рост 176.5 ≈ 50%', approx(pct('height', 176.5), 0.5, 0.01));
check('рост 190 ≈ 97–98%', pct('height', 190) > 0.96 && pct('height', 190) < 0.985, pct('height', 190).toFixed(3));
check('жим 1.0×вес у мужчин 25–34: 75–88%', pct('bench', 1.0) > 0.75 && pct('bench', 1.0) < 0.88, pct('bench', 1.0).toFixed(3));
check('доход 90k ≈ медиана', approx(pct('income', 90800), 0.5, 0.02), pct('income', 90800).toFixed(3));
check('жир 15% (lower=better) > 85%', pct('bodyfat', 15) > 0.85, pct('bodyfat', 15).toFixed(3));
check('VO2 из 5 км за 20 мин ≈ 49–50', approx(M.vo2FromRun(20), 49.8, 0.8), M.vo2FromRun(20).toFixed(1));
const ga = M.buildGroup({ region: 'russia', sex: 'male', age: 'all' });
const w55 = M.groupWorse(M.byId.height, M.buildGroup({ region: 'russia', sex: 'male', age: '55-64' }), 176.5);
check('старшие ниже ростом (176.5 у 55–64 > 50%)', w55.lo > 0.6, w55.lo.toFixed(3));
const gw = M.buildGroup({ region: 'world', sex: 'all', age: 'all' });
check('ЕГЭ н/п для «Мира»', !M.groupWorse(M.byId.ege, gw, 80));

// 5. профиль-пример целиком
const user = M.userFromProfile(DATA.exampleProfile);
const gm = M.buildGroup({ region: 'moscow', sex: 'male', age: '25-34' });
let t0 = Date.now();
const fr = M.featureResults(user, gm);
console.log('  featureResults', Date.now() - t0, 'ms');
fr.filter(r => r.status === 'ok').forEach(r => console.log('   ', r.id.padEnd(10), (100 * r.pct).toFixed(1).padStart(5) + '%', '[' + (100 * r.ci[0]).toFixed(0) + '–' + (100 * r.ci[1]).toFixed(0) + ']', r.reliability));
const fids = M.selectRarityFeatures(fr, 'strengths');
t0 = Date.now();
const rr = M.rarity(user, gm, fids);
console.log('  rarity', Date.now() - t0, 'ms; признаков', fids.length);
console.log('   наивно 1 из', (1 / rr.naive).toExponential(2), 'CI10^', rr.naiveCI.map(x => x.toFixed(2)));
console.log('   честно 1 из', (1 / rr.honest).toExponential(2), '±', (rr.honestSE / rr.honest * 100).toFixed(1) + '%', 'CI10^', rr.honestCI.map(x => x.toFixed(2)));
check('честная редкость меньше наивной', rr.honest > rr.naive);
check('МК отн. ошибка < 5%', rr.honestSE / rr.honest < 0.05, (rr.honestSE / rr.honest * 100).toFixed(2) + '%');
t0 = Date.now();
const ia = M.computeIndex('attr', user, gm);
console.log('  attr', Date.now() - t0, 'ms', (100 * ia.pct).toFixed(1), ia.ci.map(x => (100 * x).toFixed(0)), ia.conf, 'внимание ×' + ia.attention.point.toFixed(2), 'пропуски', ia.missing.join(','));
ia.contributions.forEach(c => console.log('     ', c.label.padEnd(48), c.contrib.toFixed(3)));
t0 = Date.now();
const is = M.computeIndex('ses', user, gm);
console.log('  ses', Date.now() - t0, 'ms', (100 * is.pct).toFixed(1), is.ci.map(x => (100 * x).toFixed(0)), is.conf);
t0 = Date.now();
const curve = M.rarityCurve(user, gm, fids);
console.log('  curve', Date.now() - t0, 'ms', curve.map(c => c.id + ':' + Math.log10(1 / c.naive).toFixed(1) + '/' + Math.log10(1 / c.honest).toFixed(1)).join(' '));
t0 = Date.now();
const imp = M.improvements(user, gm, fids, 'strengths');
console.log('  improvements', Date.now() - t0, 'ms');
imp.sort((a, b) => b.dAttr - a.dAttr).forEach(i => console.log('    ', i.label.padEnd(40), 'attr', (100 * i.dAttr).toFixed(1), 'ses', (100 * i.dSes).toFixed(1), 'log10N', i.dLogN.toFixed(2)));

// средний человек: перцентиль индекса ≈ 50
const avg = M.userFromProfile({ sex: 'male', age: 30, values: { height: 176.5, weight: 78, bodyfat: 23.5, bodyfatMethod: 'dxa', bench: 58, face: 5, faceSource: 'strangers', income: 90800, edu: 'bachelor', smoking: 'never', alcohol: 'rare' } });
const ia2 = M.computeIndex('attr', avg, g);
check('средний мужчина: индекс привлекательности 35–70%', ia2.pct > 0.35 && ia2.pct < 0.7, (100 * ia2.pct).toFixed(1));

// группа «все»: смесь полов создаёт корреляцию роста и силы
const gAll = M.buildGroup({ region: 'russia', sex: 'all', age: 'all' });
const tall = M.userFromProfile({ sex: 'male', age: 30, values: { height: 185, weight: 85, bench: 100 } });
const rA = M.rarity(tall, gAll, ['height', 'bench'], { draws: 0 });
check('в смешанной группе честная > наивной (пол-корреляция)', rA.honest > rA.naive * 1.3, (rA.honest / rA.naive).toFixed(2) + '×');

console.log(fails ? `\n${fails} FAIL` : '\nвсе проверки прошли');
process.exit(fails ? 1 : 0);
