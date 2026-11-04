/* =====================================================================
   ДАННЫЕ И КОЭФФИЦИЕНТЫ
   Всё, что является «знанием о мире», живёт здесь. Модель (model.js) только
   считает. Каждая цифра либо взята из источника (ключ в SOURCES), либо явно
   помечена как допущение. Правьте смело — интерфейс подхватит изменения.

   СОГЛАШЕНИЯ
   • params[region][sex] — распределение для ячейки «возраст 25–34».
     Остальные возрастные группы получаются сдвигом ageShift.
   • Все сдвиги (ageShift, special.*.shift) — в «латентных σ» и в сторону
     «лучше»: +0.3 значит «эта группа в среднем на 0.3σ лучше по признаку».
     Для normal это сдвиг среднего на 0.3·sd, для lognormal — медианы в
     exp(0.3·sigma) раз, для категорий — пробит-сдвиг накопленных долей.
     Для признаков с direction:'none' (ИМТ) сдвиг — просто «выше».
   • overrides['region|sex|age'] — прямое задание распределения ячейки
     (тогда ageShift не применяется). sex может быть 'any'.
   • Категории всегда перечислены от «хуже» к «лучше».
   • reliability: good — прямые репрезентативные данные; extrap — данные
     по соседней стране/выборке или пересчёт; rough — экспертная оценка
     по косвенным данным. От неё зависит ширина интервалов (zSD).
   ===================================================================== */
(function (root) {
  'use strict';

  // ---------- константы пересчёта ----------
  const C = {
    // Росстат, выборочное обследование зарплат, апрель 2025: медиана начисленной з/п.
    ruMedianGrossApr2025: 73871,
    // Допущение: номинальный рост зарплат апрель-2025 → конец 2026 ≈ +18% (≈12%/год).
    wageGrowthToNow: 1.18,
    // На руки = начислено × 0.87 (НДФЛ 13%; прогрессия с 2025 для высоких доходов игнорируется).
    netShare: 0.87,
    // Мужская медиана выше общей примерно на 13%, женская ниже на 13% (Росстат, гендерный разрыв ~27–30%).
    maleWagePremium: 1.13, femaleWageFactor: 0.87,
    // Москва / Россия по медиане ≈ 1.55 (Мосстат vs Росстат, допущение по соотношению средних).
    moscowWageFactor: 1.55,
    // Паритет покупательной способности, ₽ за международный $ (ICP/World Bank, экстраполяция на 2026).
    rubPerUsdPPP: 30,
    // Рыночный курс для пересчёта богатства (отчёты о богатстве в рыночных $).
    rubPerUsdMarket: 85,
  };
  const ruNetMedian = C.ruMedianGrossApr2025 * C.wageGrowthToNow * C.netShare; // ≈ 75.8 тыс.

  // ---------- источники ----------
  const SOURCES = {
    ncdrisc: { t: 'NCD-RisC (2016, обновл. 2020). A century of trends in adult human height. eLife 5:e13410; данные по когортам до 1996 г.р.', u: 'https://ncdrisc.org/data-downloads-height.html' },
    ncdriscBmi: { t: 'NCD-RisC (2024). Worldwide trends in underweight and obesity 1990–2022. Lancet 403:1027.', u: 'https://ncdrisc.org/data-downloads-adiposity.html' },
    rlms: { t: 'РМЭЗ НИУ ВШЭ (RLMS-HSE) — антропометрия, курение, алкоголь, доходы; панель 1994–2023.', u: 'https://www.hse.ru/rlms/' },
    nhanesDxa: { t: 'Kelly TL et al. (2009). DXA body composition reference values from NHANES. PLoS ONE 4(9):e7038.', u: 'https://doi.org/10.1371/journal.pone.0007038' },
    deurenberg: { t: 'Deurenberg P et al. (1991). Body mass index as a measure of body fatness: age- and sex-specific prediction formulas. Br J Nutr 65:105.', u: 'https://doi.org/10.1079/BJN19910073' },
    friend: { t: 'Kaminsky LA et al. (2015, 2022). Reference standards for cardiorespiratory fitness (FRIEND registry). Mayo Clin Proc.', u: 'https://doi.org/10.1016/j.mayocp.2021.08.020' },
    hunt: { t: 'Loe H et al. (2013). Aerobic capacity reference data in 3816 healthy men and women 20–90 years (HUNT, Норвегия). PLoS ONE 8:e64319.', u: 'https://doi.org/10.1371/journal.pone.0064319' },
    daniels: { t: 'Daniels J, Gilbert J (1979). Oxygen Power — формула VDOT: VO₂max из результата на дистанции.', u: 'https://en.wikipedia.org/wiki/Jack_Daniels_(coach)#VDOT' },
    strength: { t: 'Сводка исследований 1ПМ у нетренированных взрослых (обзоры по силовым нормам, напр. Kraemer & Ratamess; ACSM). Популяционных данных по жиму/приседу нет — распределение реконструировано.', u: 'https://www.acsm.org/' },
    strengthlevel: { t: 'StrengthLevel.com — самоотчёты ~150 млн подъёмов. ТОЛЬКО тренирующиеся и с самоотбором: «средний» там ≈ 1.0–1.2×вес в жиме у мужчин; для населения не годится, используется как верхний якорь.', u: 'https://strengthlevel.com/' },
    rosstatWage: { t: 'Росстат: выборочное обследование заработной платы, апрель 2025 — медиана 73 871 ₽ (начисленная).', u: 'https://rosstat.gov.ru/labor_market_employment_salaries' },
    wid: { t: 'World Inequality Database / World Inequality Report 2022 — распределение доходов взрослых в €/$ ППС.', u: 'https://wid.world/' },
    ubs: { t: 'UBS Global Wealth Report 2024/2025 — медиана и среднее богатства на взрослого по странам и миру.', u: 'https://www.ubs.com/global/en/family-office-uhnw/reports/global-wealth-report.html' },
    nafi: { t: 'НАФИ / ЦБ РФ — доля россиян со сбережениями (~40–50%), структура активов домохозяйств.', u: 'https://nafi.ru/' },
    census2021: { t: 'Росстат, ВПН-2021, т.3 «Образование» — уровень образования по полу и возрасту.', u: 'https://rosstat.gov.ru/vpn/2020' },
    barroLee: { t: 'Barro-Lee (2013, обновл.) / UNESCO UIS — образовательный уровень взрослых в мире.', u: 'http://www.barrolee.com/' },
    uniCounts: { t: 'Оценка автора по численности выпусков вузов (МГУ, МФТИ, ВШЭ, СПбГУ, МИФИ и др.; открытые данные вузов и мониторинг Минобрнауки) / размер когорты ~1.3 млн.', u: 'https://monitoring.miccedu.ru/' },
    fipi: { t: 'ФИПИ: аналитические отчёты ЕГЭ 2023–2025 — средние баллы по предметам (рус. ~68–70, проф. мат. ~55–60, общ. ~57).', u: 'https://fipi.ru/ege/analytic-and-methodological-materials' },
    vsosh: { t: 'ВсОШ (Минпросвещения, olimpiada.ru): ~1.5 млн участников муниципального этапа, ~9 тыс. участников финала (2026), ~2.5–3 тыс. дипломов финала в год.', u: 'https://vserosolimp.edsoo.ru/' },
    iqNorm: { t: 'IQ по определению нормирован N(100,15) на популяции стандартизации теста. Межстрановые «национальные IQ» (Lynn и др.) методологически спорны и здесь не используются.', u: 'https://en.wikipedia.org/wiki/Intelligence_quotient' },
    strenze: { t: 'Strenze T (2007). Intelligence and socioeconomic success: a meta-analytic review. Intelligence 35:401. (IQ–образование .56, –профессия .43, –доход .20)', u: 'https://doi.org/10.1016/j.intell.2006.09.004' },
    freyDetterman: { t: 'Frey MC, Detterman DK (2004). Scholastic assessment or g? Psychol Sci 15:373. (SAT–g ≈ .82)', u: 'https://doi.org/10.1111/j.0956-7976.2004.00687.x' },
    whoAlcohol: { t: 'WHO Global status report on alcohol and health (2018, 2024): ~45% мужчин и ~65% женщин в мире не пили за год; Россия ~9–10 л чистого спирта на душу 15+.', u: 'https://www.who.int/publications/i/item/9789240096745' },
    gbdAlcohol: { t: 'GBD 2016 Alcohol Collaborators (2018). Lancet 392:1015 — безопасного уровня потребления нет (для «лучше = меньше»).', u: 'https://doi.org/10.1016/S0140-6736(18)31310-2' },
    rosstatHealth: { t: 'Росстат: выборочное наблюдение состояния здоровья населения 2024 (≈99 тыс. чел. 15+): курят ежедневно или периодически 32.3% мужчин и 7.7% женщин; Москва — 29% / 10%.', u: 'https://rosstat.gov.ru/itog_inspect' },
    whoTobacco: { t: 'WHO global report on trends in prevalence of tobacco use 2000–2030 (2024): ~32% мужчин и ~7% женщин 15+.', u: 'https://www.who.int/publications/i/item/9789240088283' },
    ehis: { t: 'Eurostat EHIS 2019 и Eurobarometer Sport 2022 (45% никогда не занимаются); данные Минспорта РФ о «систематически занимающихся» (~55%) завышены по определению.', u: 'https://ec.europa.eu/eurostat/statistics-explained/index.php?title=Health-enhancing_physical_activity_statistics' },
    gem: { t: 'Global Entrepreneurship Monitor — Россия (ВШЭ/СПбГУ): ранняя предпринимательская активность ~6–9%, устоявшийся бизнес ~4–5%. Росстат ОРС: работодатели ~1.5% занятых; самозанятых >12 млн.', u: 'https://www.gemconsortium.org/economy-profiles/russia' },
    researchers: { t: 'ИСИЭЗ ВШЭ «Индикаторы науки»: ~330 тыс. исследователей в РФ; Scopus — порядка 100 тыс. российских авторов в год.', u: 'https://issek.hse.ru/news/science' },
    levadaLang: { t: 'Левада-центр (2015): 14% россиян более-менее свободно говорят хотя бы на одном иностранном языке; ВЦИОМ: свободно английским ~5%.', u: 'https://www.levada.ru/' },
    eurobarLang: { t: 'Eurobarometer 540 (2024) / Adult Education Survey — владение иностранными языками в ЕС (~35% не знают ни одного).', u: 'https://europa.eu/eurobarometer/surveys/detail/2979' },
    fomTravel: { t: 'ФОМ (2022): 69% россиян никогда не отдыхали за границей; ВЦИОМ (2022): 77% не выезжали за 5 лет.', u: 'https://fom.ru/' },
    friendsSurvey: { t: 'Survey Center on American Life (2021): 12% — ни одного близкого друга, ~49% — три и меньше, ~13% — десять и больше. ВЦИОМ: в среднем 3–4 близких друга. Самоотчёт.', u: 'https://www.americansurveycenter.org/research/the-state-of-american-friendship-change-challenges-and-loss/' },
    managers: { t: 'Росстат, обследование рабочей силы: руководители (ОКЗ 1) ≈ 7–8% занятых; доли руководителей групп и отделов — оценка.', u: 'https://rosstat.gov.ru/compendium/document/13265' },
    social: { t: 'Оценка по открытым данным о распределении подписчиков (Instagram/Telegram/VK: медиана ~100–300; >10 тыс. — около 1%).', u: '' },
    // привлекательность
    hitsch: { t: 'Hitsch GJ, Hortaçsu A, Ariely D (2010). What makes you click? Mate preferences in online dating. QME 8:393. (рост, доход, внешность; у женщин доход весомее, чем у мужчин)', u: 'https://doi.org/10.1007/s11129-010-9088-6' },
    fisman: { t: 'Fisman R et al. (2006). Gender differences in mate selection: evidence from a speed dating experiment. QJE 121:673.', u: 'https://doi.org/10.1162/qjec.2006.121.2.673' },
    asendorpf: { t: 'Asendorpf JB, Penke L, Back MD (2011). From dating to mating and relating: predictors of initial and long-term outcomes of speed-dating. Eur J Pers 25:16. (внешность — главный предиктор и для выбора мужчин)', u: 'https://doi.org/10.1002/per.768' },
    langlois: { t: 'Langlois JH et al. (2000). Maxims or myths of beauty? A meta-analytic and theoretical review. Psychol Bull 126:390.', u: 'https://doi.org/10.1037/0033-2909.126.3.390' },
    sell: { t: 'Sell A, Lukaszewski AW, Townsley M (2017). Cues of upper body strength account for most of the variance in men\'s bodily attractiveness. Proc R Soc B 284:20171819.', u: 'https://doi.org/10.1098/rspb.2017.1819' },
    frederick: { t: 'Frederick DA, Haselton MG (2007). Why is muscularity sexy? PSPB 33:1167. (мускулистые > обычные, но «очень мускулистые» — не лучше)', u: 'https://doi.org/10.1177/0146167207303022' },
    stulp: { t: 'Stulp G, Buunk AP, Pollet TV (2013). Women want taller men more than men want shorter women. PAID 54:877. Yancey & Emerson (2016): ~49% женщин хотят только партнёра выше себя.', u: 'https://doi.org/10.1016/j.paid.2012.12.019' },
    walter: { t: 'Walter KV et al. (2020). Sex differences in mate preferences across 45 countries. Psychol Sci 31:408. (ресурсы и статус важнее для женщин во всех культурах)', u: 'https://doi.org/10.1177/0956797620904154' },
    eastwick: { t: 'Eastwick PW et al. (2014). The predictive validity of ideal partner preferences: a review and meta-analysis. Psychol Bull 140:623. (заявленные предпочтения слабо предсказывают реальный выбор)', u: 'https://doi.org/10.1037/a0032432' },
    bruch: { t: 'Bruch EE, Newman MEJ (2018). Aspirational pursuit of mates in online dating markets. Sci Adv 4:eaap9815. (иерархия желанности; у мужчин пик ~50 лет, связь с доходом и образованием)', u: 'https://doi.org/10.1126/sciadv.aap9815' },
    okcupid: { t: 'Rudder C (2014). Dataclysm; блог OkCupid: женщины оценивают ~80% мужчин «ниже среднего» — сильная асимметрия внимания.', u: 'https://www.gwern.net/docs/psychology/okcupid/' },
    tinderGini: { t: '«Tinder experiments II» (2015, неакадемический анализ): Джини распределения лайков мужчинам ≈ 0.58. Грубая оценка.', u: 'https://medium.com/@worstonlinedater/tinder-experiments-ii-guys-unless-you-are-really-hot-you-are-probably-better-off-not-wasting-your-2ddf370a6e9a' },
    jonason: { t: 'Jonason PK et al. (2015). Relationship dealbreakers: traits people avoid in potential mates. PSPB 41:1697. (курение, неопрятность, пассивность — частые «стоп-факторы»)', u: 'https://doi.org/10.1177/0146167215609064' },
    place: { t: 'Place SS et al. (2010). Humans show mate copying after observing real mate choices. Evol Hum Behav 31:320. (социальное доказательство)', u: 'https://doi.org/10.1016/j.evolhumbehav.2010.02.001' },
    selfRating: { t: 'Epley N, Whitchurch E (2008). Mirror, mirror on the wall: enhancement in self-recognition. PSPB 34:1159; Greitemeyer (2020): непривлекательные люди сильнее переоценивают себя.', u: 'https://doi.org/10.1177/0146167208318601' },
    judgeCable: { t: 'Judge TA, Cable DM (2004). The effect of physical height on workplace success and income. J Appl Psychol 89:428.', u: 'https://doi.org/10.1037/0021-9010.89.3.428' },
    ses: { t: 'Индексы SES: Hollingshead (1975), Duncan SEI, ISEI (Ganzeboom 1992) — доход, образование, профессиональный статус. Веса в этом приложении — экспертное допущение.', u: 'https://doi.org/10.1016/0049-089X(92)90017-B' },
    corrLit: { t: 'Матрица корреляций собрана из мета-анализов (Strenze 2007; Judge & Cable 2004; Langlois 2000; Frey & Detterman 2004) и популяционных исследований физподготовки; где прямых данных нет — экспертная оценка. Затем спектр обрезан до ближайшей положительно определённой.', u: '' },
  };

  // ---------- группы ----------
  const GROUPS = {
    regions: [
      { id: 'world', label: 'Мир' },
      { id: 'russia', label: 'Россия' },
      { id: 'moscow', label: 'Москва' },
    ],
    sexes: [
      { id: 'male', label: 'Мужчины' },
      { id: 'female', label: 'Женщины' },
      { id: 'all', label: 'Все' },
    ],
    ages: [
      { id: '18-24', label: '18–24', range: [18, 24] },
      { id: '25-34', label: '25–34', range: [25, 34] },
      { id: '35-44', label: '35–44', range: [35, 44] },
      { id: '45-54', label: '45–54', range: [45, 54] },
      { id: '55-64', label: '55–64', range: [55, 64] },
    ],
    // доли возрастных групп среди 18–64 (ООН WPP 2024 / Росстат, округлено)
    ageWeights: {
      world: { '18-24': 0.16, '25-34': 0.24, '35-44': 0.22, '45-54': 0.20, '55-64': 0.18 },
      russia: { '18-24': 0.11, '25-34': 0.19, '35-44': 0.26, '45-54': 0.22, '55-64': 0.22 },
      moscow: { '18-24': 0.09, '25-34': 0.20, '35-44': 0.27, '45-54': 0.22, '55-64': 0.22 },
    },
    // численность 18–64 (оба пола), чтобы перевести долю в «столько людей»
    popSize: { world: 4.95e9, russia: 86e6, moscow: 8.6e6, topuni: 1.5e5 },
    special: [
      { id: 'none', label: '—' },
      { id: 'topuni', label: 'Студенты топ-вузов РФ', forces: { region: 'moscow', age: '18-24' },
        note: 'Студенты топ-15 вузов (МГУ, МФТИ, ВШЭ, СПбГУ, МИФИ, Бауманка, МГИМО…), 18–24. Строится как «Москва 18–24» с поправками; грубая оценка.' },
    ],
  };

  const REL = {
    good: { label: 'хорошие данные', short: 'данные', zSD: 0.07 },
    extrap: { label: 'экстраполяция', short: 'экстрап.', zSD: 0.18 },
    rough: { label: 'грубая оценка', short: 'грубо', zSD: 0.33 },
    na: { label: 'нет данных', short: 'н/д', zSD: 0 },
  };

  const SECTIONS = [
    { id: 'about', label: 'Кто ты' },
    { id: 'body', label: 'Тело' },
    { id: 'looks', label: 'Внешность' },
    { id: 'mind', label: 'Образование и интеллект' },
    { id: 'money', label: 'Деньги' },
    { id: 'life', label: 'Образ жизни' },
    { id: 'achieve', label: 'Достижения' },
    { id: 'social', label: 'Социальное положение' },
  ];

  // shorthand для категорий
  const cats = (arr) => arr.map(([id, label]) => ({ id, label }));
  const bothSexes = (p) => ({ male: p, female: p });

  // ---------- признаки ----------
  const FEATURES = [
    // ===== ТЕЛО =====
    {
      id: 'height', section: 'body', label: 'Рост', unit: 'см', short: 'Рост',
      input: { kind: 'number', min: 140, max: 225, step: 0.5, placeholder: '180' },
      direction: 'higher', type: 'normal',
      params: {
        world: { male: { mean: 171.0, sd: 7.3 }, female: { mean: 159.5, sd: 6.8 } },
        russia: { male: { mean: 176.5, sd: 6.8 }, female: { mean: 165.3, sd: 6.2 } },
        moscow: { male: { mean: 177.5, sd: 6.8 }, female: { mean: 166.0, sd: 6.2 } },
      },
      // секулярный тренд + усадка с возрастом
      ageShift: { '18-24': 0.02, '25-34': 0, '35-44': -0.12, '45-54': -0.28, '55-64': -0.45 },
      special: { topuni: { shift: 0.1 } },
      reliability: { world: 'good', russia: 'good', moscow: 'extrap' },
      noise: { sd: 1.0 },
      improve: null,
      sources: ['ncdrisc', 'rlms'],
      note: 'Мир — среднее по странам, взвешенное по населению (широкая смесь; реальное распределение тяжелее нормального). Москва: +1 см к России (городская надбавка в РМЭЗ), экстраполяция.',
    },
    {
      id: 'bmi', section: 'body', label: 'ИМТ (из роста и веса)', unit: 'кг/м²', short: 'ИМТ',
      derived: true, direction: 'none', type: 'lognormal', descriptive: true,
      params: {
        world: { male: { median: 24.3, sigma: 0.16 }, female: { median: 24.5, sigma: 0.2 } },
        russia: { male: { median: 25.0, sigma: 0.15 }, female: { median: 23.6, sigma: 0.19 } },
        moscow: { male: { median: 24.8, sigma: 0.15 }, female: { median: 23.2, sigma: 0.19 } },
      },
      ageShift: { '18-24': -0.45, '25-34': 0, '35-44': 0.35, '45-54': 0.6, '55-64': 0.75 },
      special: { topuni: { shift: -0.2 } },
      reliability: { world: 'good', russia: 'good', moscow: 'extrap' },
      sources: ['ncdriscBmi', 'rlms'],
      note: 'Справочно, без направления «лучше/хуже»: ИМТ не отличает мышцы от жира. В «один из N» и индексы не входит, но используется для оценки % жира, если он не введён.',
    },
    {
      id: 'bodyfat', section: 'body', label: 'Процент жира', unit: '%', short: '% жира',
      input: { kind: 'number', min: 3, max: 60, step: 0.5, placeholder: '18' },
      method: {
        key: 'bodyfatMethod', label: 'Как измерен',
        options: [
          { id: 'dxa', label: 'DEXA / гидровзвешивание', sd: 1.5, bias: 0 },
          { id: 'caliper', label: 'Калипер (у специалиста)', sd: 3, bias: 1 },
          { id: 'bia', label: 'Умные весы / биоимпеданс', sd: 4.5, bias: 0 },
          { id: 'eye', label: 'На глаз / по фото', sd: 5, bias: 3 },
        ],
        default: 'bia',
        note: 'Калипер и оценка «на глаз» в среднем занижают % жира относительно DEXA на 1–4 п.п. — модель добавляет эту поправку.',
      },
      direction: 'lower', type: 'normal',
      params: {
        world: { male: { mean: 23.5, sd: 7.0 }, female: { mean: 33.5, sd: 7.0 } },
        russia: { male: { mean: 23.5, sd: 6.8 }, female: { mean: 32.5, sd: 7.2 } },
        moscow: { male: { mean: 23.0, sd: 6.6 }, female: { mean: 31.5, sd: 7.0 } },
      },
      ageShift: { '18-24': 0.3, '25-34': 0, '35-44': -0.25, '45-54': -0.42, '55-64': -0.55 },
      special: { topuni: { shift: 0.15 } },
      reliability: { world: 'extrap', russia: 'extrap', moscow: 'extrap' },
      improve: { delta: -4, label: '−4 п.п. жира', effort: 'месяцы' },
      sources: ['nhanesDxa', 'deurenberg', 'rlms'],
      note: 'Популяционных DEXA-данных по России нет: взяты референсы NHANES (США, мужчины 20–39 ≈ 26% по DEXA) со сдвигом на меньшую долю ожирения в РФ (по ИМТ). Если не введён — оценивается по ИМТ и возрасту формулой Deurenberg (±5 п.п.).',
    },
    {
      id: 'bench', section: 'body', label: 'Жим лёжа (1ПМ)', unit: 'кг', short: 'Жим/вес',
      displayUnit: '× вес тела',
      input: { kind: 'number', min: 0, max: 400, step: 2.5, placeholder: '80' },
      direction: 'higher', type: 'lognormal',
      params: {
        world: { male: { median: 0.72, sigma: 0.34 }, female: { median: 0.37, sigma: 0.34 } },
        russia: { male: { median: 0.75, sigma: 0.33 }, female: { median: 0.38, sigma: 0.33 } },
        moscow: { male: { median: 0.76, sigma: 0.33 }, female: { median: 0.39, sigma: 0.33 } },
      },
      ageShift: { '18-24': 0, '25-34': 0, '35-44': -0.15, '45-54': -0.38, '55-64': -0.65 },
      reliability: { world: 'rough', russia: 'rough', moscow: 'rough' },
      noise: { logSd: 0.04 },
      improve: { factor: 1.15, label: '+15% к жиму', effort: '3–6 мес.' },
      sources: ['strength', 'strengthlevel'],
      note: 'Считается относительно веса тела. По реконструкции: жмут свой вес ~19% мужчин 25–34, 1.5× — ~2%, 2× — ~0.2%. На StrengthLevel «средний» результат выше, потому что там только тренирующиеся (самоотбор).',
    },
    {
      id: 'squat', section: 'body', label: 'Присед (1ПМ)', unit: 'кг', short: 'Присед/вес',
      displayUnit: '× вес тела',
      input: { kind: 'number', min: 0, max: 500, step: 2.5, placeholder: '100' },
      direction: 'higher', type: 'lognormal',
      params: {
        world: { male: { median: 0.92, sigma: 0.36 }, female: { median: 0.58, sigma: 0.38 } },
        russia: { male: { median: 0.95, sigma: 0.35 }, female: { median: 0.6, sigma: 0.38 } },
        moscow: { male: { median: 0.95, sigma: 0.35 }, female: { median: 0.6, sigma: 0.38 } },
      },
      ageShift: { '18-24': 0.02, '25-34': 0, '35-44': -0.15, '45-54': -0.38, '55-64': -0.65 },
      reliability: { world: 'rough', russia: 'rough', moscow: 'rough' },
      noise: { logSd: 0.05 },
      improve: { factor: 1.2, label: '+20% к приседу', effort: '3–6 мес.' },
      sources: ['strength', 'strengthlevel'],
      note: 'Полный присед (бедро ниже параллели). Мужчины: 1.5× вес — ~10%, 2× — ~2% (реконструкция).',
    },
    {
      id: 'vo2', section: 'body', label: 'Выносливость: VO₂max', unit: 'мл/кг/мин', short: 'VO₂max',
      input: { kind: 'number', min: 15, max: 90, step: 0.5, placeholder: '45' },
      alt: { key: 'run5k', label: 'или время 5 км (мин)', min: 12, max: 60, step: 0.1, placeholder: '25' },
      method: {
        key: 'vo2Method', label: 'Откуда VO₂max',
        options: [
          { id: 'lab', label: 'Лабораторный тест', sd: 1.5, bias: 0 },
          { id: 'watch', label: 'Часы (Garmin/Apple и т.п.)', sd: 3.5, bias: -1 },
          { id: 'run', label: 'Пересчёт из 5 км', sd: 3, bias: 0 },
        ],
        default: 'watch',
      },
      direction: 'higher', type: 'normal',
      params: {
        world: { male: { mean: 43, sd: 8.5 }, female: { mean: 34, sd: 7 } },
        russia: { male: { mean: 44, sd: 8.5 }, female: { mean: 34.5, sd: 7 } },
        moscow: { male: { mean: 44, sd: 8.5 }, female: { mean: 34.5, sd: 7 } },
      },
      ageShift: { '18-24': 0.28, '25-34': 0, '35-44': -0.5, '45-54': -0.98, '55-64': -1.45 },
      special: { topuni: { shift: 0.1 } },
      reliability: { world: 'extrap', russia: 'extrap', moscow: 'extrap' },
      improve: { delta: 4, label: '+4 VO₂max (≈ −2 мин на 5 км)', effort: '2–4 мес.' },
      sources: ['friend', 'hunt', 'daniels'],
      note: 'Российских популяционных данных нет — среднее между FRIEND (США, ниже) и HUNT (Норвегия, выше), минус поправка на то, что тестируются более здоровые. Время на 5 км переводится в VO₂max по формуле Daniels–Gilbert (VDOT).',
    },

    // ===== ВНЕШНОСТЬ =====
    {
      id: 'face', section: 'looks', label: 'Внешность (оценка лица другими)', unit: '/10', short: 'Внешность',
      input: { kind: 'number', min: 1, max: 10, step: 0.1, placeholder: '5.5' },
      method: {
        key: 'faceSource', label: 'Чья оценка',
        options: [
          { id: 'strangers', label: 'Незнакомцы (Photofeeler и т.п., 20+ оценок)', sd: 0.5, bias: 0 },
          { id: 'friends', label: 'Знакомые / друзья', sd: 1.0, bias: -0.6 },
          { id: 'self', label: 'Сам себе', sd: 1.5, bias: -0.8 },
        ],
        default: 'self',
        note: 'Самооценка привлекательности в среднем завышена (Epley & Whitchurch 2008), друзья тоже льстят — вводится поправка вниз и большая неопределённость.',
      },
      direction: 'higher', type: 'normal',
      params: { world: bothSexes({ mean: 5, sd: 1.5 }), russia: bothSexes({ mean: 5, sd: 1.5 }), moscow: bothSexes({ mean: 5, sd: 1.5 }) },
      reliability: { world: 'rough', russia: 'rough', moscow: 'rough' },
      improve: { delta: 0.5, label: '+0.5 балла (стрижка, кожа, одежда, фото)', effort: 'недели' },
      sources: ['langlois', 'selfRating'],
      note: 'Шкала задана как относительная: 5 = средний среди сверстников своего пола, σ = 1.5. Распределение известно «по построению», ненадёжен сам ввод — поэтому «грубо».',
    },

    // ===== ОБРАЗОВАНИЕ И ИНТЕЛЛЕКТ =====
    {
      id: 'edu', section: 'mind', label: 'Уровень образования', short: 'Образование',
      input: { kind: 'select' },
      direction: 'higher', type: 'categorical',
      categories: cats([['school', 'Школа или ниже'], ['spo', 'Колледж / техникум (СПО)'], ['student', 'Неоконченное высшее / студент'],
        ['bachelor', 'Бакалавр / специалист'], ['master', 'Магистр / два высших'], ['phd', 'Кандидат наук / PhD'], ['dsc', 'Доктор наук']]),
      params: {
        world: { male: { probs: [62, 9, 3.5, 19, 5.5, 0.9, 0.02] }, female: { probs: [59, 9, 3.5, 21, 6.5, 0.8, 0.01] } },
        russia: { male: { probs: [22, 34, 5, 32, 6, 0.9, 0.02] }, female: { probs: [13, 28, 5, 43, 10, 1.0, 0.02] } },
        moscow: { male: { probs: [12, 20, 6, 45, 15, 2.0, 0.06] }, female: { probs: [8, 15, 6, 50, 18.5, 2.4, 0.05] } },
      },
      overrides: {
        'world|male|18-24': { probs: [72, 8, 12, 7, 1, 0.01, 0.001] },
        'world|female|18-24': { probs: [68, 8, 14, 9, 1, 0.01, 0.001] },
        'russia|male|18-24': { probs: [38, 27, 24, 10, 1, 0.02, 0.001] },
        'russia|female|18-24': { probs: [30, 22, 30, 16, 2, 0.03, 0.001] },
        'moscow|male|18-24': { probs: [25, 17, 38, 17, 3, 0.05, 0.001] },
        'moscow|female|18-24': { probs: [20, 13, 42, 21, 4, 0.05, 0.001] },
      },
      ageShift: { '35-44': -0.05, '45-54': -0.15, '55-64': -0.25 },
      special: { topuni: { params: bothSexes({ probs: [0.5, 0.5, 80, 14, 5, 0.01, 0.001] }) } },
      reliability: { world: 'extrap', russia: 'good', moscow: 'good' },
      improve: { steps: 1, label: 'следующая ступень образования', effort: 'годы' },
      sources: ['census2021', 'barroLee'],
      note: 'Россия/Москва — перепись 2021 по возрасту 25–34 (доли магистров/кандидатов внутри «высшего» — оценка). Мир — Barro-Lee/UNESCO, категории сведены приблизительно.',
    },
    {
      id: 'uni', section: 'mind', label: 'Престиж вуза (лучший, где учился)', short: 'Вуз',
      input: { kind: 'select' },
      direction: 'higher', type: 'categorical',
      categories: cats([['none', 'Не учился в вузе'], ['regular', 'Обычный вуз'], ['strong', 'Сильный вуз (топ-50 РФ / сильный нац. вуз)'],
        ['top15', 'Топ-15 РФ (МГИМО, Бауманка, ИТМО, НГУ, Политех…)'], ['top5', 'Топ-5 РФ (МГУ, МФТИ, ВШЭ, СПбГУ, МИФИ)'], ['world50', 'Мировой топ-50 (QS/THE)']]),
      params: {
        world: bothSexes({ probs: [72, 22.5, 4, 1, 0.4, 0.15] }),
        russia: { male: { probs: [57, 30, 8, 3.2, 1.9, 0.1] }, female: { probs: [50, 36, 8.5, 3.4, 2.0, 0.1] } },
        moscow: { male: { probs: [38, 32, 12, 9, 8.5, 0.6] }, female: { probs: [33, 36, 12.5, 9.5, 8.5, 0.6] } },
      },
      ageShift: { '18-24': -0.05, '35-44': -0.05, '45-54': -0.12, '55-64': -0.2 },
      special: { topuni: { params: bothSexes({ probs: [0.01, 0.01, 0.01, 28, 70, 2] }) } },
      reliability: { world: 'rough', russia: 'extrap', moscow: 'extrap' },
      improve: null,
      sources: ['uniCounts', 'census2021'],
      note: 'Топ-5 РФ выпускают ~25–30 тыс. человек в год при когорте ~1.3 млн → ≈2%. Для Москвы доля выше из-за притока выпускников. «Мир» — категории по смыслу (национальные аналоги), очень грубо.',
    },
    {
      id: 'ege', section: 'mind', label: 'ЕГЭ: средний балл по 3 предметам', unit: 'балл', short: 'ЕГЭ',
      input: { kind: 'number', min: 20, max: 100, step: 0.5, placeholder: '75' },
      direction: 'higher', type: 'normal',
      applies: { regions: ['russia', 'moscow'], ages: ['18-24', '25-34'] },
      params: {
        russia: { male: { mean: 63, sd: 12.5 }, female: { mean: 65, sd: 12 } },
        moscow: { male: { mean: 69, sd: 12 }, female: { mean: 71, sd: 11.5 } },
      },
      special: { topuni: { params: bothSexes({ mean: 88, sd: 6 }) } },
      reliability: { world: 'na', russia: 'extrap', moscow: 'extrap' },
      improve: null,
      sources: ['fipi'],
      note: 'Среди сдававших ЕГЭ (≈ рождённые с 1991 г.). ФИПИ публикует распределения по предметам, а не по сумме трёх — SD суммы оценена. Шкалы разных лет не идеально сопоставимы. Для «Мира» не применимо.',
    },
    {
      id: 'olymp', section: 'mind', label: 'Олимпиады (высший уровень)', short: 'Олимпиады',
      input: { kind: 'select' },
      direction: 'higher', type: 'categorical',
      applies: { regions: ['russia', 'moscow'] },
      categories: cats([['none', 'Не участвовал / школьный этап'], ['muni', 'Муниципальный этап'], ['region', 'Региональный этап — участник'],
        ['regionPrize', 'Региональный этап — призёр/победитель'], ['final', 'Финал ВсОШ / перечневая 1-го уровня — участник'],
        ['finalPrize', 'Финал ВсОШ — призёр/победитель (или диплом 1-го уровня)'], ['intl', 'Международная олимпиада — медаль']]),
      params: {
        russia: bothSexes({ probs: [70, 20.5, 6.5, 2.2, 0.55, 0.25, 0.005] }),
        moscow: bothSexes({ probs: [54, 28, 10, 5, 1.9, 0.9, 0.03] }),
      },
      special: { topuni: { params: bothSexes({ probs: [20, 15, 20, 20, 12, 12, 1] }) } },
      reliability: { world: 'na', russia: 'extrap', moscow: 'rough' },
      improve: null,
      sources: ['vsosh'],
      note: 'Доли на когорту (~1.3 млн): финал ВсОШ ≈ 4–5 тыс. уникальных школьников, призёры ≈ 2 тыс. Москва даёт непропорционально много призёров (~1/3 при ~9% населения).',
    },
    {
      id: 'iq', section: 'mind', label: 'IQ (полноценный тест)', unit: '', short: 'IQ',
      input: { kind: 'number', min: 55, max: 165, step: 1, placeholder: '115' },
      method: {
        key: 'iqSource', label: 'Какой тест',
        options: [
          { id: 'proctored', label: 'Очно у психолога (WAIS, Равен, Амтхауэр)', sd: 5, bias: 0 },
          { id: 'mensa', label: 'Тест Mensa / нормированный онлайн с контролем', sd: 7, bias: -3 },
          { id: 'online', label: 'Случайный онлайн-тест', sd: 10, bias: -10 },
        ],
        default: 'online',
        note: 'Популярные онлайн-тесты систематически завышают результат — поправка −10.',
      },
      direction: 'higher', type: 'normal',
      params: { world: bothSexes({ mean: 100, sd: 15 }), russia: bothSexes({ mean: 100, sd: 15 }), moscow: bothSexes({ mean: 103, sd: 15 }) },
      special: { topuni: { params: bothSexes({ mean: 118, sd: 11 }) } },
      reliability: { world: 'extrap', russia: 'good', moscow: 'extrap' },
      improve: null,
      sources: ['iqNorm', 'strenze'],
      note: 'IQ нормирован по возрасту, поэтому возрастного сдвига нет. Москва +3 — допущение (городская надбавка в когнитивных тестах). Топ-вузы: ~118 (по связи SAT/ЕГЭ с g).',
    },

    // ===== ДЕНЬГИ =====
    {
      id: 'income', section: 'money', label: 'Доход на руки в месяц (все источники)', unit: '₽', short: 'Доход',
      input: { kind: 'number', min: 0, max: 1e8, step: 1000, placeholder: '120000' },
      direction: 'higher', type: 'lognormal',
      params: {
        // Мир: в ₽ по ППС (≈30 ₽/$): медиана заработка мужчины 25–34 ≈ $900 ППС/мес.
        world: { male: { median: 900 * C.rubPerUsdPPP, sigma: 1.0 }, female: { median: 600 * C.rubPerUsdPPP, sigma: 1.05 } },
        russia: { male: { median: ruNetMedian * C.maleWagePremium * 1.06, sigma: 0.65 }, female: { median: ruNetMedian * C.femaleWageFactor * 1.03, sigma: 0.62 } },
        moscow: { male: { median: ruNetMedian * C.maleWagePremium * 1.06 * C.moscowWageFactor, sigma: 0.75 }, female: { median: ruNetMedian * C.femaleWageFactor * 1.03 * C.moscowWageFactor, sigma: 0.72 } },
      },
      ageShift: { '18-24': -0.7, '25-34': 0, '35-44': 0.05, '45-54': -0.1, '55-64': -0.35 },
      special: { topuni: { shift: -0.35 } },
      reliability: { world: 'rough', russia: 'good', moscow: 'extrap' },
      noise: { logSd: 0.05 },
      improve: { factor: 1.3, label: '+30% к доходу', effort: '1–2 года' },
      sources: ['rosstatWage', 'wid'],
      note: 'Среди тех, у кого есть доход. Россия: медиана Росстата (апрель 2025) × рост зарплат до 2026 × 0.87 (НДФЛ) × поправки на пол и возраст. Москва: ×1.55 (экстраполяция). Мир: пересчёт ₽ по ППС, WID — грубо. Высокие доходы в опросах недоучитываются, реальный правый хвост толще.',
    },
    {
      id: 'networth', section: 'money', label: 'Чистые активы (всё имущество − долги)', unit: '₽', short: 'Активы',
      input: { kind: 'number', min: -1e9, max: 1e11, step: 10000, placeholder: '1500000' },
      direction: 'higher', type: 'lognormal',
      params: {
        world: { male: { median: 5200 * C.rubPerUsdMarket, sigma: 2.1, zeroMass: 0.15 }, female: { median: 4700 * C.rubPerUsdMarket, sigma: 2.1, zeroMass: 0.17 } },
        russia: { male: { median: 440e3, sigma: 1.6, zeroMass: 0.15 }, female: { median: 400e3, sigma: 1.6, zeroMass: 0.16 } },
        moscow: { male: { median: 1.55e6, sigma: 1.6, zeroMass: 0.12 }, female: { median: 1.4e6, sigma: 1.6, zeroMass: 0.13 } },
      },
      ageShift: { '18-24': -0.6, '25-34': 0, '35-44': 0.35, '45-54': 0.6, '55-64': 0.75 },
      special: { topuni: { shift: 0.1 } },
      reliability: { world: 'rough', russia: 'rough', moscow: 'rough' },
      noise: { logSd: 0.15 },
      improve: { factor: 1.5, label: '+50% к активам', effort: '1–3 года' },
      sources: ['ubs', 'nafi'],
      note: 'Включая долю в жилье, машину, вклады, инвестиции. UBS: медиана богатства взрослого в РФ ≈ $8 тыс. (в основном жильё), для 25–34 меньше. ~15% имеют нулевые или отрицательные активы (одна «ступенька» внизу).',
    },

    // ===== ОБРАЗ ЖИЗНИ =====
    {
      id: 'alcohol', section: 'life', label: 'Алкоголь', short: 'Алкоголь',
      input: { kind: 'select' },
      direction: 'higher', type: 'categorical',
      categories: cats([['heavy', 'Запои или >28 порций в неделю'], ['high', '15–28 порций в неделю'], ['moderate', '8–14 порций в неделю'],
        ['light', '1–7 порций в неделю'], ['rare', 'Реже раза в неделю'], ['none', 'Не пью совсем']]),
      categoryNote: '1 порция ≈ 10 г спирта: 250 мл пива, 100 мл вина, 30 мл водки.',
      params: {
        world: { male: { probs: [2, 4, 7, 18, 22, 47] }, female: { probs: [0.5, 1, 2, 10, 21, 65.5] } },
        russia: { male: { probs: [3, 5, 9, 28, 37, 18] }, female: { probs: [0.5, 1.5, 4, 22, 45, 27] } },
        moscow: { male: { probs: [2, 4, 9, 30, 37, 18] }, female: { probs: [0.5, 1.5, 5, 25, 43, 25] } },
      },
      ageShift: { '18-24': 0.15, '35-44': -0.08, '45-54': -0.1, '55-64': 0 },
      reliability: { world: 'extrap', russia: 'extrap', moscow: 'rough' },
      improve: { steps: 1, label: 'пить на ступень меньше', effort: 'сразу' },
      sources: ['whoAlcohol', 'rlms', 'gbdAlcohol'],
      note: '«Лучше» = меньше (GBD 2018: безопасного уровня нет). Самоотчёты занижают потребление в 1.5–2 раза — если честно указываете своё, вы выглядите хуже людей, которые врут опросам. Это смещение не исправлено.',
    },
    {
      id: 'smoking', section: 'life', label: 'Курение (сигареты, IQOS, вейп)', short: 'Курение',
      input: { kind: 'select' },
      direction: 'higher', type: 'categorical',
      categories: cats([['daily', 'Курю ежедневно'], ['sometimes', 'Время от времени'], ['former', 'Бросил'], ['never', 'Никогда не курил']]),
      params: {
        world: { male: { probs: [28, 4, 13, 55] }, female: { probs: [6, 1.5, 4, 88.5] } },
        russia: { male: { probs: [28, 5, 15, 52] }, female: { probs: [6.5, 2.5, 8, 83] } },
        moscow: { male: { probs: [25, 5, 16, 54] }, female: { probs: [8, 3, 9, 80] } },
      },
      ageShift: { '18-24': 0.05, '35-44': -0.05, '45-54': -0.05, '55-64': 0 },
      special: { topuni: { shift: 0.3 } },
      reliability: { world: 'good', russia: 'good', moscow: 'good' },
      improve: { toCategory: 'former', label: 'бросить курить', effort: 'сразу (но тяжело)' },
      sources: ['rosstatHealth', 'whoTobacco'],
      note: 'Росстат 2024: курят 32.3% мужчин и 7.7% женщин; в Москве 29% и 10%. Распределение «бросил / никогда» — по РМЭЗ, экстраполяция.',
    },
    {
      id: 'training', section: 'life', label: 'Тренировки (≥30 мин, в неделю, последние 3 мес.)', short: 'Спорт',
      input: { kind: 'select' },
      direction: 'higher', type: 'categorical',
      categories: cats([['0', 'Не тренируюсь'], ['1', '1 раз'], ['2-3', '2–3 раза'], ['4-5', '4–5 раз'], ['6+', '6 и больше']]),
      params: {
        world: { male: { probs: [60, 12, 17, 7, 4] }, female: { probs: [68, 11, 14, 5, 2] } },
        russia: { male: { probs: [50, 13, 22, 10, 5] }, female: { probs: [55, 14, 20, 8, 3] } },
        moscow: { male: { probs: [42, 13, 26, 13, 6] }, female: { probs: [47, 14, 24, 11, 4] } },
      },
      ageShift: { '18-24': 0.15, '35-44': -0.1, '45-54': -0.2, '55-64': -0.3 },
      special: { topuni: { shift: 0.15 } },
      reliability: { world: 'rough', russia: 'rough', moscow: 'rough' },
      improve: { steps: 1, label: 'на одну тренировку в неделю больше', effort: 'сразу' },
      sources: ['ehis', 'rlms'],
      note: 'Именно целенаправленные тренировки (зал, бег, секция), а не ходьба. Официальная цифра Минспорта (~55% «систематически занимаются») сильно завышена определением — ориентир Eurobarometer/EHIS.',
    },

    // ===== ДОСТИЖЕНИЯ =====
    {
      id: 'business', section: 'achieve', label: 'Свой бизнес / проекты', short: 'Бизнес',
      input: { kind: 'select' },
      direction: 'higher', type: 'categorical',
      categories: cats([['none', 'Нет'], ['side', 'Пет-проект / фриланс с доходом'], ['own', 'Свой бизнес (ИП/ООО) с регулярной выручкой'],
        ['employer', 'Бизнес с сотрудниками (≥5 чел.)'], ['big', 'Выручка >100 млн ₽/год или успешный exit']]),
      params: {
        world: { male: { probs: [62, 20, 14, 3.5, 0.3] }, female: { probs: [70, 18, 10, 1.8, 0.15] } },
        russia: { male: { probs: [76, 16, 6, 1.7, 0.25] }, female: { probs: [84, 12, 3.2, 0.7, 0.08] } },
        moscow: { male: { probs: [70, 18, 8, 3, 0.6] }, female: { probs: [80, 13, 5, 1.5, 0.2] } },
      },
      ageShift: { '18-24': -0.35, '35-44': 0.1, '45-54': 0.12, '55-64': 0 },
      special: { topuni: { shift: 0.1 } },
      reliability: { world: 'rough', russia: 'rough', moscow: 'rough' },
      improve: { steps: 1, label: 'следующий уровень бизнеса', effort: '1–3 года' },
      sources: ['gem'],
      note: 'Мир: в бедных странах много неформальной самозанятости, поэтому «свой бизнес» там чаще, но мельче. Это одна из причин, почему межстрановые сравнения здесь грубые.',
    },
    {
      id: 'pubs', section: 'achieve', label: 'Научные публикации', short: 'Публикации',
      input: { kind: 'select' },
      direction: 'higher', type: 'categorical',
      categories: cats([['none', 'Нет'], ['any', 'Есть (тезисы, РИНЦ, ВАК)'], ['scopus1', '≥1 статья в Scopus/WoS'], ['scopus5', '≥5 статей Scopus/WoS'], ['h10', 'h-индекс ≥ 10']]),
      params: {
        world: bothSexes({ probs: [96, 3.3, 0.5, 0.2, 0.03] }),
        russia: bothSexes({ probs: [93, 5.9, 0.6, 0.25, 0.03] }),
        moscow: bothSexes({ probs: [83, 13, 2.5, 1.2, 0.2] }),
      },
      ageShift: { '18-24': -0.2, '35-44': 0.1, '45-54': 0.15, '55-64': 0.15 },
      special: { topuni: { params: bothSexes({ probs: [55, 38, 5, 1.8, 0.2] }) } },
      reliability: { world: 'rough', russia: 'rough', moscow: 'rough' },
      improve: { steps: 1, label: 'следующий уровень публикаций', effort: '1–2 года' },
      sources: ['researchers'],
      note: 'Россия — оценка по числу исследователей и авторов Scopus; Москва концентрирует науку (~×3). Много «любых» публикаций из-за требований магистратуры.',
    },
    {
      id: 'languages', section: 'achieve', label: 'Иностранные языки на уровне ≥B2 (свободный разговор)', short: 'Языки',
      input: { kind: 'select' },
      direction: 'higher', type: 'categorical',
      categories: cats([['0', 'Ни одного'], ['1', 'Один'], ['2', 'Два'], ['3+', 'Три и больше']]),
      params: {
        world: bothSexes({ probs: [57, 30, 10, 3] }),
        russia: { male: { probs: [80, 17, 2.5, 0.5] }, female: { probs: [78, 18.5, 3, 0.5] } },
        moscow: { male: { probs: [62, 31, 6, 1] }, female: { probs: [60, 32, 7, 1] } },
      },
      ageShift: { '18-24': 0.1, '35-44': -0.15, '45-54': -0.3, '55-64': -0.4 },
      special: { topuni: { params: bothSexes({ probs: [15, 60, 20, 5] }) } },
      reliability: { world: 'rough', russia: 'extrap', moscow: 'rough' },
      improve: { steps: 1, label: '+1 язык до B2', effort: '1–2 года' },
      sources: ['levadaLang', 'eurobarLang'],
      note: 'Левада (2015): 14% всех россиян говорят более-менее свободно хотя бы на одном языке; у 25–34 выше. Самоотчёты завышают уровень. Мир: в многоязычных странах (Индия, Африка) второй язык — норма, поэтому мир «сильнее» России.',
    },
    {
      id: 'countries', section: 'achieve', label: 'Страны, где побывал (кроме своей)', unit: 'стран', short: 'Страны',
      input: { kind: 'number', min: 0, max: 200, step: 1, placeholder: '10' },
      direction: 'higher', type: 'lognormal', discrete: true,
      params: {
        world: bothSexes({ median: 3, sigma: 1.1, zeroMass: 0.6 }),
        russia: bothSexes({ median: 4, sigma: 1.0, zeroMass: 0.5 }),
        moscow: bothSexes({ median: 8, sigma: 0.95, zeroMass: 0.2 }),
      },
      ageShift: { '18-24': -0.2, '35-44': 0.05, '45-54': -0.05, '55-64': -0.15 },
      special: { topuni: { shift: 0.4 } },
      reliability: { world: 'rough', russia: 'rough', moscow: 'rough' },
      improve: { delta: 5, label: '+5 стран', effort: '1–2 года' },
      sources: ['fomTravel'],
      note: 'ФОМ 2022: 69% россиян никогда не отдыхали за границей (все возрасты; с учётом поездок в СНГ и к родственникам доля без выездов ниже). Среди выезжавших — лог-нормальное распределение числа стран.',
    },

    // ===== СОЦИАЛЬНОЕ =====
    {
      id: 'leadership', section: 'social', label: 'Руководство: сколько людей в подчинении', short: 'Руководство',
      input: { kind: 'select' },
      direction: 'higher', type: 'categorical',
      categories: cats([['0', 'Нет подчинённых'], ['1-5', '1–5 человек'], ['6-30', '6–30'], ['31-200', '31–200'], ['200+', '200+ / топ-менеджмент']]),
      params: {
        world: { male: { probs: [82, 11, 5, 1.6, 0.4] }, female: { probs: [88, 8, 3, 0.8, 0.2] } },
        russia: { male: { probs: [78, 13, 6, 2.4, 0.6] }, female: { probs: [85, 9, 4.5, 1.3, 0.2] } },
        moscow: { male: { probs: [70, 16, 9, 4, 1] }, female: { probs: [78, 12, 7, 2.5, 0.5] } },
      },
      ageShift: { '18-24': -0.5, '35-44': 0.2, '45-54': 0.25, '55-64': 0.15 },
      special: { topuni: { shift: -0.2 } },
      reliability: { world: 'rough', russia: 'extrap', moscow: 'rough' },
      improve: { steps: 1, label: 'следующая ступень руководства', effort: '1–3 года' },
      sources: ['managers'],
      note: 'Включая руководство в своём бизнесе. Доля руководителей в РФ по ОРС ~7–8% занятых; разбивка по размеру команды — оценка.',
    },
    {
      id: 'friends', section: 'social', label: 'Близкие друзья (к кому можно обратиться с серьёзной проблемой)', unit: 'чел.', short: 'Друзья',
      input: { kind: 'number', min: 0, max: 100, step: 1, placeholder: '4' },
      direction: 'higher', type: 'lognormal', discrete: true,
      params: { world: bothSexes({ median: 3.5, sigma: 0.75, zeroMass: 0.1 }), russia: bothSexes({ median: 3.5, sigma: 0.75, zeroMass: 0.1 }), moscow: bothSexes({ median: 3.5, sigma: 0.75, zeroMass: 0.1 }) },
      ageShift: { '18-24': 0.2, '35-44': -0.1, '45-54': -0.15, '55-64': -0.15 },
      reliability: { world: 'rough', russia: 'rough', moscow: 'rough' },
      improve: { delta: 2, label: '+2 близких друга', effort: '1–2 года' },
      sources: ['friendsSurvey'],
      note: 'Данные США (2021) и ВЦИОМ, перенесены на все регионы. Самоотчёт: люди понимают «близкого друга» по-разному.',
    },
    {
      id: 'audience', section: 'social', label: 'Аудитория (подписчики в главной соцсети/канале)', unit: 'чел.', short: 'Аудитория',
      input: { kind: 'number', min: 0, max: 1e9, step: 1, placeholder: '500' },
      direction: 'higher', type: 'lognormal', discrete: true,
      params: {
        world: bothSexes({ median: 120, sigma: 1.8, zeroMass: 0.35 }),
        russia: bothSexes({ median: 150, sigma: 1.8, zeroMass: 0.15 }),
        moscow: bothSexes({ median: 200, sigma: 1.8, zeroMass: 0.1 }),
      },
      ageShift: { '18-24': 0.2, '35-44': -0.1, '45-54': -0.3, '55-64': -0.5 },
      reliability: { world: 'rough', russia: 'rough', moscow: 'rough' },
      improve: { factor: 3, label: '×3 аудитория', effort: '1–2 года' },
      sources: ['social'],
      note: 'Очень грубо: >10 тыс. подписчиков ≈ 1% людей с соцсетями, >100 тыс. ≈ 0.05%.',
    },
  ];

  // ---------- корреляции (латентные, в направлении «лучше», внутри пола×возраста) ----------
  // Пол и возраст сами по себе создают дополнительные корреляции — они учитываются
  // автоматически, потому что смешанные группы считаются как смесь ячеек.
  const CORRELATIONS = [
    // тело
    ['height', 'income', 0.10], ['height', 'edu', 0.10], ['height', 'iq', 0.10], ['height', 'face', 0.10], ['height', 'uni', 0.06], ['height', 'leadership', 0.08],
    ['bodyfat', 'bench', 0.35], ['bodyfat', 'squat', 0.35], ['bodyfat', 'vo2', 0.55], ['bodyfat', 'face', 0.25], ['bodyfat', 'training', 0.35],
    ['bodyfat', 'alcohol', 0.10], ['bodyfat', 'edu', 0.12], ['bodyfat', 'income', 0.05], ['bodyfat', 'smoking', 0.0],
    ['bench', 'squat', 0.75], ['bench', 'vo2', 0.15], ['squat', 'vo2', 0.25],
    ['bench', 'training', 0.50], ['squat', 'training', 0.50], ['vo2', 'training', 0.45],
    ['vo2', 'smoking', 0.15], ['vo2', 'alcohol', 0.10],
    // внешность
    ['face', 'income', 0.08], ['face', 'friends', 0.12], ['face', 'audience', 0.15], ['face', 'training', 0.10],
    // образование и интеллект
    ['edu', 'uni', 0.70], ['edu', 'ege', 0.45], ['edu', 'iq', 0.50], ['edu', 'olymp', 0.30], ['edu', 'income', 0.35], ['edu', 'networth', 0.25],
    ['edu', 'smoking', 0.25], ['edu', 'training', 0.20], ['edu', 'pubs', 0.35], ['edu', 'languages', 0.40], ['edu', 'countries', 0.30],
    ['edu', 'leadership', 0.30], ['edu', 'business', 0.05],
    ['uni', 'ege', 0.60], ['uni', 'olymp', 0.45], ['uni', 'iq', 0.50], ['uni', 'income', 0.30], ['uni', 'networth', 0.20], ['uni', 'pubs', 0.30],
    ['uni', 'languages', 0.35], ['uni', 'countries', 0.30], ['uni', 'leadership', 0.20], ['uni', 'smoking', 0.10],
    ['ege', 'olymp', 0.45], ['ege', 'iq', 0.65], ['ege', 'income', 0.20], ['ege', 'languages', 0.30], ['ege', 'pubs', 0.20],
    ['olymp', 'iq', 0.45], ['olymp', 'pubs', 0.25], ['olymp', 'income', 0.12],
    ['iq', 'income', 0.22], ['iq', 'leadership', 0.20], ['iq', 'pubs', 0.25], ['iq', 'languages', 0.25], ['iq', 'networth', 0.15], ['iq', 'smoking', 0.10],
    // деньги
    ['income', 'networth', 0.50], ['income', 'leadership', 0.45], ['income', 'business', 0.25], ['income', 'countries', 0.40],
    ['income', 'languages', 0.25], ['income', 'training', 0.12], ['income', 'friends', 0.10],
    ['networth', 'business', 0.30], ['networth', 'countries', 0.35], ['networth', 'leadership', 0.30],
    // образ жизни
    ['alcohol', 'smoking', 0.35], ['smoking', 'training', 0.15], ['alcohol', 'friends', -0.10],
    // достижения, социальное
    ['business', 'leadership', 0.45], ['business', 'audience', 0.15], ['business', 'countries', 0.15],
    ['pubs', 'languages', 0.25], ['languages', 'countries', 0.45],
    ['leadership', 'friends', 0.10], ['friends', 'audience', 0.20], ['training', 'friends', 0.05],
  ];

  // ---------- индекс конвенциональной привлекательности для женщин ----------
  // U = Σ w_k · s_k + штрафы. s_k — оценки компонент примерно в σ-единицах.
  // Кривые — кусочно-линейные [x, s]. Веса — синтез: внешность доминирует
  // (Asendorpf 2011, Langlois 2000), рост с порогом (Stulp 2013, Hitsch 2010),
  // тело ≈ сила верха + низкий жир (Sell 2017, Frederick & Haselton 2007),
  // ресурсы с убывающей отдачей (Hitsch 2010, Walter 2020), статус (Bruch 2018).
  const ATTRACTIVENESS = {
    sex: 'male',
    components: [
      { id: 'face', label: 'Лицо', short: 'Лицо', weight: 0.36, kind: 'latent', feature: 'face', sources: ['asendorpf', 'langlois', 'fisman'] },
      {
        id: 'height', label: 'Рост', short: 'Рост', weight: 0.15, kind: 'curve', feature: 'height',
        // точки для России (средний мужчина 176.5); для других групп сдвигаются на разницу средних
        anchorMean: 176.5,
        curve: [[155, -3], [160, -2.6], [165, -2.0], [170, -1.2], [173, -0.7], [176, -0.2], [178, 0.05], [180, 0.3], [183, 0.55], [186, 0.7], [190, 0.75], [194, 0.65], [198, 0.35], [205, -0.2]],
        sources: ['stulp', 'hitsch'],
        note: 'Порог: ниже ~173 см штраф растёт круто («хочу выше себя на каблуках»), 183–192 — плато, выше 195 — небольшой спад.',
      },
      {
        id: 'body', label: 'Тело: жир + сила', short: 'Тело', weight: 0.18, kind: 'body',
        fatCurve: [[6, 0.4], [9, 0.75], [12, 0.8], [15, 0.6], [18, 0.25], [21, -0.15], [25, -0.7], [30, -1.4], [35, -2.0], [45, -2.8]],
        muscleCurve: [[0.3, -1.0], [0.5, -0.6], [0.7, -0.15], [0.9, 0.25], [1.1, 0.55], [1.3, 0.8], [1.6, 0.95], [2.0, 1.0], [2.4, 0.9]],
        fatShare: 0.55, squatToBench: 0.72,
        sources: ['sell', 'frederick'],
        note: 'Сила верха тела объясняет ~70% дисперсии оценок мужского тела (Sell 2017), но эффект насыщается: «очень мускулистый» не лучше «мускулистого».',
      },
      { id: 'resources', label: 'Ресурсы: доход, активы', short: 'Ресурсы', weight: 0.14, kind: 'mix', parts: [['income', 0.7], ['networth', 0.3]], saturate: 1.6, sources: ['hitsch', 'walter'] },
      { id: 'status', label: 'Статус: образование, вуз, руководство, бизнес', short: 'Статус', weight: 0.08, kind: 'mix', parts: [['edu', 0.35], ['uni', 0.2], ['leadership', 0.3], ['business', 0.15]], saturate: 2, sources: ['bruch', 'walter', 'fisman'] },
      { id: 'fitness', label: 'Активность: спорт, выносливость', short: 'Активность', weight: 0.04, kind: 'mix', parts: [['training', 0.5], ['vo2', 0.5]], saturate: 2, sources: ['frederick'] },
      { id: 'social', label: 'Социальное доказательство: друзья, аудитория', short: 'Соц. доказательство', weight: 0.05, kind: 'mix', parts: [['friends', 0.6], ['audience', 0.4]], saturate: 2, sources: ['place'] },
    ],
    penalties: [
      { feature: 'smoking', category: 'daily', value: -0.45, label: 'Курит ежедневно' },
      { feature: 'smoking', category: 'sometimes', value: -0.15, label: 'Курит иногда' },
      { feature: 'alcohol', category: 'heavy', value: -0.6, label: 'Много пьёт' },
      { feature: 'alcohol', category: 'high', value: -0.25, label: 'Пьёт выше умеренного' },
    ],
    weightUncertainty: 0.3,   // лог-нормальный разброс каждого веса
    penaltyUncertainty: 0.4,
    curveUncertainty: 0.25,   // масштаб кривых роста/тела ±25%
    // Перевод перцентиля в «относительное внимание на дейтинг-приложениях»:
    // лог-нормаль с Джини ≈ 0.58 → sigma = √2·Φ⁻¹((G+1)/2) ≈ 1.14
    attentionSigma: 1.14,
    sources: ['hitsch', 'fisman', 'asendorpf', 'langlois', 'sell', 'frederick', 'stulp', 'walter', 'eastwick', 'bruch', 'okcupid', 'tinderGini', 'jonason', 'place'],
    caveats: [
      'Индекс описывает «среднюю» конвенциональную оценку — реальные предпочтения у разных женщин сильно расходятся, а заявленные предпочтения слабо предсказывают реальный выбор (Eastwick 2014).',
      'Не учтены харизма, юмор, доброта, уверенность, запах, голос, совместимость — они часто важнее всего перечисленного, но не измеряются анкетой.',
      'Возраст не входит в индекс: сравнение всегда со сверстниками. В онлайн-дейтинге желанность мужчин растёт примерно до 50 лет (Bruch & Newman 2018).',
      'Веса — синтез нескольких исследований, а не одна оценённая модель; их неопределённость разыгрывается в Монте-Карло.',
    ],
  };

  // ---------- индекс социального положения (SES) ----------
  const SES = {
    components: [
      { feature: 'income', weight: 0.28, label: 'Доход' },
      { feature: 'networth', weight: 0.18, label: 'Активы' },
      { feature: 'edu', weight: 0.16, label: 'Образование' },
      { feature: 'uni', weight: 0.06, label: 'Престиж вуза' },
      { feature: 'leadership', weight: 0.16, label: 'Руководство' },
      { feature: 'business', weight: 0.08, label: 'Собственность / бизнес' },
      { feature: 'friends', weight: 0.04, label: 'Социальный капитал' },
      { feature: 'audience', weight: 0.04, label: 'Публичность' },
    ],
    saturate: 3,
    weightUncertainty: 0.3,
    sources: ['ses', 'strenze'],
    caveats: [
      'Классические индексы SES строятся из дохода, образования и профессионального статуса; здесь добавлены активы и немного социального капитала. Веса — допущение.',
      'Индекс относительный: перцентиль среди выбранной группы. «Мир» — очень разнородная группа, и доход в ₽ по ППС делает почти любого москвича «верхним».',
    ],
  };

  // ---------- пример профиля (вымышленный) ----------
  const EXAMPLE_PROFILE = {
    version: 1, name: 'Пример: вымышленный москвич 27 лет',
    sex: 'male', age: 27, home: 'moscow',
    values: {
      height: 181, weight: 79, bodyfat: 17, bodyfatMethod: 'bia', bench: 85, squat: 110,
      vo2: '', run5k: 24.5, vo2Method: 'run', face: 6, faceSource: 'friends',
      edu: 'master', uni: 'top15', ege: 82, olymp: 'region', iq: '', iqSource: 'online',
      income: 180000, networth: 2500000, alcohol: 'light', smoking: 'never', training: '2-3',
      business: 'side', pubs: 'none', languages: '1', countries: 14, leadership: '1-5', friends: 5, audience: 700,
    },
  };

  const DATA = { constants: C, sources: SOURCES, groups: GROUPS, reliability: REL, sections: SECTIONS,
    features: FEATURES, correlations: CORRELATIONS, attractiveness: ATTRACTIVENESS, ses: SES, exampleProfile: EXAMPLE_PROFILE };
  if (typeof module !== 'undefined' && module.exports) module.exports = DATA;
  else root.DATA = DATA;
})(typeof window !== 'undefined' ? window : globalThis);
