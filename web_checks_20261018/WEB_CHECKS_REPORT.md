# Веб-проверки перед подачей Paper 1 в IJF

**Дата обращения ко всем источникам: 2026-10-26 (UTC).** Папка называется `web_checks_20261018`, как указано в задании. Снимки лежат рядом с отчётом. Префикс имени файла совпадает с номером пункта.

## Как читать отчёт

- **Способы доступа:** curl, headless Chromium (Playwright), инструмент WebFetch, инструмент WebSearch, открытые API (arXiv, OSF, Crossref, Semantic Scholar, Elsevier API без ключа, raw.githubusercontent.com). Логин нигде не использовался, ничего не отправлялось.
- **Метки у цитат:**
  - без метки — цитата из сырого HTML, PDF, JSON или текста, сохранённого в папке;
  - **[WF]** — цитата получена через WebFetch. Сырой HTML недоступен, а WebFetch отдаёт выдержку, сделанную моделью. Дословность запрашивалась, но сверить её с исходником нельзя;
  - **[WS]** — пересказ поисковой выдачи. Это не цитата со страницы, только подсказка, где проверять вручную.
- **Что заблокировано:**

| Сайт | curl | Chromium | WebFetch | Чем ответил |
|---|---|---|---|---|
| sciencedirect.com (Guide for Authors, редакционная статья) | 403 | 403 | 403 | Cloudflare / блок-страница Elsevier «There was a problem providing the content you requested … CPE00001» |
| forecasters.org/ijf/* (= ijf.forecasters.org) | 403 | 403 | **работает** | bunny.net «Bunny Shield»: PoW-проверка проходит, после перезагрузки снова 403 |
| tennis-data.co.uk | 403 | 403 | 403 | Cloudflare «Sorry, you have been blocked» |
| cardiff.ac.uk | — | 403 | 403 | Cloudflare «Just a moment…» |
| papers.ssrn.com | 403 | — | — | Cloudflare challenge |
| osf.io (HTML-страница препринта) | — | 403 | — | Работает API api.osf.io |
| web.archive.org / archive.ph | сброс соединения / 429 | — | «unable to fetch» | — |
| cris.cobiss.net, wiwi.hu-berlin.de | — | HTTP 200, но вместо содержимого страница Anubis «Oh noes! … Access Denied» | cobiss: тоже страница Anubis «Access Denied»; hu-berlin: не пробовался | Anubis (защита от ботов) |

---

## 1. Требования IJF к рукописи

**Главный источник, Guide for Authors на ScienceDirect, открыть не удалось.** Ни curl, ни браузер, ни WebFetch, ни веб-архивы его не отдали (снимок блок-страницы: `1-01_sciencedirect_guide_for_authors_403_block.html`). Ссылка «Instructions for Authors» в Editorial Manager ведёт на тот же адрес. Поэтому статусы ниже опираются на доступные страницы:

- страницы IJF на forecasters.org (через WebFetch);
- официальный LaTeX-шаблон IJF. Он скачивается по ссылке «Please use this template» со страницы IJF «For authors»;
- страница журнала на shop.elsevier.com;
- **общие** страницы Elsevier. Они не относятся именно к IJF, и это отмечено в каждой строке.

Пересказ поисковой выдачи по самому Guide for Authors лежит в `1-07_websearch_indirect_guide_for_authors.md` [WS].

| Что проверяли | Результат (статус) | URL | Цитата | Дата | Файл |
|---|---|---|---|---|---|
| Guide for Authors (ScienceDirect) | **Не удалось открыть** (403) | https://www.sciencedirect.com/journal/international-journal-of-forecasting/publish/guide-for-authors | Блок-страница: «There was a problem providing the content you requested» | 2026-10-26 | 1-01 |
| Длина аннотации | Guide: не проверено. Шаблон IJF: **рекомендовано** писать кратко, без формул и ссылок. Лимит в словах **не упоминается** | https://docs.google.com/uc?id=0B4rHhz_bQTXIQTI4aXNjclUxbHM&export=download (ссылка со страницы https://forecasters.org/ijf/authors/) | «This is the abstract. Keep it brief and avoid mathematical notation and citations.» | 2026-10-26 | 1-04 |
| Keywords: сколько, из какого списка | Список IJF **рекомендован**. Число ключевых слов и обязательность списка на странице **не упоминаются** [WF]. В списке 102 слова [WF]. Есть: «Sports forecasting», «Calibration», «Probability forecasting». Нет: «Prediction markets», «Betting markets», «Tennis», «Forecast evaluation» (вместо него есть «Evaluating forecasts») [WF] | https://forecasters.org/ijf/keywords/ (редирект с https://ijf.forecasters.org/keywords/) | «The following set of keywords is recommended to assist in this process.» [WF]. В шаблоне: «% Suggested keywords are listed at https://ijf.forecasters.org/keywords/» | 2026-10-26 | 1-03, 1-04 |
| Highlights: нужны ли, сколько, лимит, формат файла | Для IJF: **не проверено** (Guide 403). [WS]: в чек-листе Guide highlights указаны как «applicable». Общая страница Elsevier (не IJF): от трёх до пяти пунктов, до 85 знаков с пробелами; не нужны до этапа финальных файлов; подаются документом Word | https://www.elsevier.com/researcher/author/tools-and-resources/highlights | «Highlights are three to five (three to four for Cell Press articles) bullet points…» / «Each Highlight can be no more than 85 characters, including spaces» / «Not part of editorial consideration and not required until the final files stage» / «Must be provided as a Word document— select "Highlights" from the drop-down list when uploading files» | 2026-10-26 | 1-08 |
| Title page: отдельный файл, что на ней | На доступных страницах **не упоминается**. В шаблоне IJF блок авторов закомментирован ради слепого рецензирования | шаблон (см. выше) | «%% Leave this section commented out so that the paper is blinded for review.» / «%% Only give the email address of the corresponding author» | 2026-10-26 | 1-04 |
| Двойное слепое | **Применяется** журналом. Что убирать из рукописи, по шаблону: блок авторов и благодарности, если они раскрывают авторов. Про метаданные файла на доступных страницах **не упоминается** | https://shop.elsevier.com/journals/international-journal-of-forecasting/0169-2070 ; https://forecasters.org/ijf/ [WF] | «To ensure fairness and objectivity, double-blind reviewing will be used.» (shop.elsevier.com, сырой HTML; та же фраза на forecasters.org/ijf [WF]). В шаблоне: «Comment this section out if it reveals the authors' identities.» | 2026-10-26 | 1-05, 1-04, 2-01 |
| Лимит длины статьи | **Не найдено** на доступных страницах (Guide 403) | — | — | 2026-10-26 | — |
| Формат фигур | Форматы указаны на странице IJF «For authors» [WF]. Отдельные файлы, отдельные подписи, заголовки над графиками: **не упоминается** на доступных страницах. [WS]: в чек-листе Guide есть пункт про «figure and table captions» | https://forecasters.org/ijf/authors/ | «Make sure all figures are saved in eps or pdf format.» / «Do not use jpg or wmf formats.» / «Figures should be of high resolution.» [WF] | 2026-10-26 | 1-02 |
| Таблицы: редактируемые? | **Не упоминается** на доступных страницах | — | — | 2026-10-26 | — |
| Раздел про генеративный ИИ: заголовок и место | Для IJF: **не проверено**. [WS]: Guide требует декларацию при подаче и отсылает к политике Elsevier. По общей политике Elsevier (не IJF): отдельный раздел в конце рукописи, сразу перед списком литературы | https://www.elsevier.com/about/policies-and-standards/generative-ai-policies-for-journals | «you must include a separate declaration section at the end of your manuscript, immediately before the references, titled for instance: “Declaration of generative AI and AI-assisted technologies in the manuscript preparation process.”» / «Title of section: Declaration of generative AI and AI-assisted technologies in the manuscript preparation process» | 2026-10-26 | 1-09 |
| Competing interests, funding: где | На доступных страницах **не найдено**. [WS]: заявление о конфликте интересов составляется через инструмент и загружается на шаге «Attach Files». В шаблоне IJF финансирование указано в разделе Acknowledgements | шаблон (см. выше) | «\section*{Acknowledgements} … Thank people. List funding agencies. Comment this section out if it reveals the authors' identities.» | 2026-10-26 | 1-04, 1-07 |
| Data and code: что при подаче, что при принятии | **Обязательно** с июля 2023 года, если главный редактор не примет обоснование, почему нельзя [WF]. Проверка воспроизводимости проводится в конце рецензирования и является условием принятия [WF]. Нужно ли сдавать данные и код **при подаче**, страница прямо **не говорит** [WF]. Шаблон: при подаче только PDF, исходники LaTeX после принятия | https://forecasters.org/ijf/ ; https://forecasters.org/ijf/authors/ ; https://shop.elsevier.com/journals/international-journal-of-forecasting/0169-2070 | «From July 2023, the IJF has enforced a new publication policy, that makes data and code sharing mandatory,» [WF] / «at the end of the review and editorial process, manuscript acceptance will be conditioned to passing a reproducibility check.» [WF] / «Authors are requested to submit computer code and data which can be made available as an online supplement to the paper.» [WF] / «Data and computer programs associated with articles published in the International Journal of Forecasting are provided as online supplements on ScienceDirect.» (shop.elsevier.com) / В шаблоне: «You only need to submit the pdf file, not the source files. If your article is accepted for publication, you will be asked for the source files.» | 2026-10-26 | 2-01, 1-02, 1-05, 1-04 |
| Стиль ссылок, нужны ли DOI | Стиль: author-year, `model5-names`, `\citet`/`\citep`; BibTeX/BibLaTeX; для EndNote стиль APA. Про DOI на доступных страницах **не упоминается** | шаблон; https://forecasters.org/ijf/authors/ | «\documentclass[11pt,3p,review,authoryear]{elsarticle}» / «\bibliographystyle{model5-names}» / «\biboptions{longnamesfirst}» / «% Please use \citet and \citep for citations.» / «Use BibLaTeX or BibTeX to ensure all cited papers are listed in the bibliography.» [WF] / «If you use EndNote for references, please use the APA style.» [WF] | 2026-10-26 | 1-04, 1-02 |
| Система подачи | Editorial Manager | https://www.editorialmanager.com/ijf (ссылка «Submit an article» на странице IJF «For authors» [WF]) | «Welcome to Editorial Manager ® for International Journal of Forecasting» (отрисованный фрейм mainpage.html) | 2026-10-26 | 1-06 |

Замечание к строке про Editorial Manager. В HTML страницы `default.aspx` есть элемент с текстом «Important Message: Site under development. Do not use for live manuscript submission.». Но у его контейнера `style="display: none;"`, и в браузере вычисленное значение `display` тоже `none`. **На отрисованной странице этот текст не показывается.**

---

## 2. Политика воспроизводимости IJF

| Что проверяли | Результат | URL | Цитата | Дата | Файл |
|---|---|---|---|---|---|
| Отдельная страница про data and code sharing на ijf.forecasters.org | Отдельной страницы **не найдено**. Политика опубликована на главной странице IJF под заголовком «Data and code sharing, as well as reproducibility policy» [WF] | https://forecasters.org/ijf/ | «From July 2023, the IJF has enforced a new publication policy, that makes data and code sharing mandatory,» [WF] / «We expect that, in practice, more than 90% of the papers the journal publishes will be accompanied by data and code.» [WF] | 2026-10-26 | 2-01 |
| Что требуют и когда (по странице IJF) | Данные и код обязательны. Проверка проходит в конце рецензирования и является условием принятия [WF] | https://forecasters.org/ijf/ | «we will now systematically submit papers through reproducibility checks» [WF] / «at the end of the review and editorial process, manuscript acceptance will be conditioned to passing a reproducibility check.» [WF] | 2026-10-26 | 2-01 |
| Кто проверяет (по странице IJF) | Процесс ведёт главный редактор. Третья сторона (CASCaD и т. п.) на странице **не упоминается** [WF] | https://forecasters.org/ijf/ | «The reproducibility check process is led by the Editor-in-Chief.» [WF] | 2026-10-26 | 2-01 |
| Исходы проверки (по странице IJF) | pass / minor concerns / major discrepancies [WF] | https://forecasters.org/ijf/ | pass: «in that case, the paper is accepted and sent to the production team for final publication;» / minor concerns: «The authors will be given a chance to clarify the situation and double-check...» (WebFetch обрезал фразу) / major: «In that case, the paper cannot be accepted for publication.» [WF] | 2026-10-26 | 2-01 |
| Формат пакета | На странице IJF **не упоминается** [WF] | https://forecasters.org/ijf/ | — | 2026-10-26 | 2-01 |
| Данные, которые нельзя выкладывать | Нужно обоснование для главного редактора [WF] | https://forecasters.org/ijf/ | «unless authors provide acceptable motivations to the Editor-in-Chief of the journal» … «for why the data and/or code cannot be shared.» [WF] | 2026-10-26 | 2-01 |
| Команда воспроизводимости (страница редакции) | Reproducibility Editor и три Reproducibility Associate Editors [WF] | https://forecasters.org/ijf/editors/ | «Bahman Rostami-Tabar — Reproducibility Editor, Cardiff University, UK»; «Miguel C. Herculano — Reproducibility Associate Editor, University of Glasgow, Adam Smith Business School, UK»; «Yangzhuoran Fin Yang — Reproducibility Associate Editor, Maastricht University, The Netherlands»; «Daniele Girolimetto — Reproducibility Associate Editor, University of Padova, Italy» [WF] | 2026-10-26 | 3-09 |
| Редакционная статья, DOI 10.1016/j.ijforecast.2026.08.004: метаданные | Название: «Editorial: Reproducibility at the International Journal of Forecasting». Авторы по Crossref: Pierre Pinson, Christophe Pérignon, Olivier Akmansoy, Nesrine Dali, Bahman Rostami-Tabar. Elsevier API: «Available online 11 September 2026», `openaccess` = 0. Volume, issue и страницы в Crossref пусты | https://api.crossref.org/works/10.1016/j.ijforecast.2026.08.004 ; https://api.elsevier.com/content/article/doi/10.1016/j.ijforecast.2026.08.004 | «<prism:coverDisplayDate>Available online 11 September 2026</prism:coverDisplayDate><openaccess>0</openaccess><openaccessArticle>false</openaccessArticle>» | 2026-10-26 | 2-02 |
| Редакционная статья: полный текст / аннотация | Полный текст **не открыт**: статья не в открытом доступе, ScienceDirect отвечает 403. **Аннотации нет** в Crossref (`abstract` = null), в Semantic Scholar (`"abstract": null`) и в ответе Elsevier API без ключа (там только coredata). Поэтому четыре вопроса (что требуют, кто проверяет, формат пакета, закрытые данные) по самой статье **не выписаны** | https://doi.org/10.1016/j.ijforecast.2026.08.004 | Semantic Scholar: `"isOpenAccess": false`, `"status": "CLOSED"` | 2026-10-26 | 2-02 |
| Новость Cardiff University о Reproducibility Editor | **Не открыта** (403, Cloudflare). [WS]: в выдаче упоминаются CASCaD, «over 100 research papers each year» и назначение в феврале 2026 года. Не проверено | https://www.cardiff.ac.uk/news/view/3021790-professor-bahman-rostami-tabar-appointed-reproducibility-editor-for-the-international-journal-of-forecasting | — | 2026-10-26 | 2-03 |

---

## 3. Рецензенты

### 3A. Должность, вуз, рабочая почта

Почты выписаны только в том написании, в каком они стоят на странице. По шаблону вуза ничего не достраивалось.

| Рецензент | Должность и подразделение (как на странице) | Почта (как написана на странице) | URL | Цитата | Дата | Файл |
|---|---|---|---|---|---|---|
| Karl Whelan | «Full Professor Of Economics», «School of Economics», University College Dublin | `karl.whelan@ucd.ie` (ссылка mailto) | https://people.ucd.ie/karl.whelan | «Karl Whelan has been Professor of Economics at University College Dublin since 2007.» / «In recent years, he has published extensively on the economics of betting and prediction markets.» | 2026-10-26 | 3-01 |
| Michael P. Clements | «Professor of Econometrics», «Research Division Lead», ICMA Centre | `m.p.clements@icmacentre.ac.uk` (ссылка mailto) | https://www.icmacentre.ac.uk/people/professor-michael-clements | «Michael P Clements is Professor of Econometrics at the ICMA Centre, Henley Business School, University of Reading.» | 2026-10-26 | 3-02 |
| Gustav Šír | «Ing. Gustav Šír, Ph.D.». Department: «Employee», «Intelligent Data Analysis», «Intelligent Data Analysis Research Group». Faculty of Electrical Engineering, CTU. Название должности на странице **не указано** | `gustav.sir@cvut.cz` (ссылка mailto) | https://fel.cvut.cz/en/faculty/people/210-gustav-sir | «Ing. Gustav Šír, Ph.D. +420224357691 gustav.sir@cvut.cz Resslova 307/9 Praha, E-435» | 2026-10-26 | 3-03 |
| Erik Štrumbelj | «Prof. dr. Erik Štrumbelj», «Full Professor», Faculty of Computer and Information Science, UL. На странице лаборатории: «Erik Štrumbelj, predstojnik laboratorija» (Laboratorij za podatkovne vede) | **На официальной странице почты нет**: вместо неё ссылка «E: Send a message» на форму связи. COBISS/SICRIS отдаёт страницу Anubis «Access Denied» | https://fri.uni-lj.si/en/about-faculty/employees/erik-strumbelj ; https://fri.uni-lj.si/sl/laboratorij/lpv | «Prof. dr. Erik Štrumbelj Full Professor T: +386 1 479 8235 E:Send a message» | 2026-10-26 | 3-04, 3-05 |
| David Forrest | «Emeritus Prof David Forrest», «Professor of Economics», «Economics», «Part of School of Management», «Faculty of Humanities and Social Sciences», University of Liverpool | `David.Forrest@liverpool.ac.uk` (ссылка mailto) | https://www.liverpool.ac.uk/people/david-forrest (сюда же ведёт редирект с /management/staff/david-forrest) | «Emeritus Prof David Forrest … Professor of Economics … Contact David.Forrest@liverpool.ac.uk» | 2026-10-26 | 3-06 |
| Fabian Wunderlich (запасной) | Deutsche Sporthochschule Köln, Institut für Trainingswissenschaft und Sportinformatik, Abt. Sportinformatik und Sportspielforschung. Указан в разделе «Wissenschaftliche Mitarbeiterinnen und Mitarbeiter» как «Dr. Fabian Wunderlich». Дата обновления страницы команды: «Zuletzt aktualisiert: 08.09.2026» | Страница команды: `f.wunderlich(at)dshs-koeln.de`. Профиль в FIS DSHS: `f.wunderlich@dshs-koeln.de` | https://www.dshs-koeln.de/universitaet/organisation/institute-einrichtungen/institut-fuer-trainingswissenschaft-und-sportinformatik/abt-sportinformatik-und-sportspielforschung/leitung-und-team ; https://fis.dshs-koeln.de/de/persons/fabian-wunderlich/ | «Dr. Fabian Wunderlich … phone +49 221 4982-4845 mail f.wunderlich(at)dshs-koeln.de» / FIS: «Institut für Trainingswissenschaft und Sportinformatik, Abteilung Sportinformatik und Sportspielforschung … E-Mail f.wunderlich@dshs-koeln.de» | 2026-10-26 | 3-07, 3-08 |

Дополнительно по Clements. Страница Henley https://www.henley.ac.uk/people/person/professor-michael-clements отдаёт 404.

### 3B. Редакция IJF

Страница редакции https://forecasters.org/ijf/editors/ доступна только через WebFetch, снимок: `3-09`. Областей экспертизы на ней нет: «The page lists editors' names, titles, affiliations, and emails, but no research areas, expertise, or keywords.» [WF]

**Входит ли кто-то из шестерых в текущую редакцию.**

| Что проверяли | Результат | URL | Цитата | Дата | Файл |
|---|---|---|---|---|---|
| Whelan, Šír, Štrumbelj, Forrest, Wunderlich на странице редакции | **Не найдены** ни в текущих, ни в прошлых разделах [WF] | https://forecasters.org/ijf/editors/ | «Whelan: Not found.» … «Wunderlich: Not found.» [WF] | 2026-10-26 | 3-09 |
| Clements на странице редакции | Есть **только в разделе «Past Editors»**, 2002–2012. В текущих разделах (Editor-in-Chief, Editors, Associate Editors, Book Review Editor, Reproducibility team) его нет [WF] | https://forecasters.org/ijf/editors/ | «"Michael P. Clements" appears under the heading "Past Editors," with the dates "2002 – 2012."» [WF] | 2026-10-26 | 3-09 |
| Clements: что пишет его собственная страница | Там указаны другие годы (2001–2012) и сказано, что после этого он был associate editor. Это расходится со страницей IJF | https://www.icmacentre.ac.uk/people/professor-michael-clements | «He served as an editor of the International Journal of Forecasting between 2001 and 2012, and since standing down from this role has served as an associate editor.» | 2026-10-26 | 3-02 |

**Члены редакции, работающие по спорту, ставкам или prediction markets.**

Как искали. Поскольку на странице IJF нет областей экспертизы, сделан скрининг по Crossref:

- **A:** статьи в IJF (ISSN 0169-2070) по запросам betting / sports / football / soccer / tennis / prediction markets / horse racing / gambling и т. п., с отбором по ключевым словам в названии;
- **B:** по каждому члену редакции, запрос `query.author` плюс тематические слова.

Авторы сопоставлялись с редакцией по фамилии и первой букве имени. Совпадения потом сверялись с официальными профилями или записями публикаций. Скрининг не исчерпывающий: кто-то мог не попасть, если его работы по теме не нашлись в Crossref по этим словам. Сырые результаты: `3-14_board_crossref_screen.json`.

| Член редакции (как на странице IJF [WF]) | Что найдено | URL | Цитата | Дата | Файл |
|---|---|---|---|---|---|
| I. McHale — «University of Salford, UK» [WF] | Официальный профиль Liverpool: «Professor of Sports Analytics». Профиль сам называет его associate editor IJF. Работы в IJF по Crossref: теннис 2011, NFL 2013, крикет 2016 и 2019, футбол 2017 и 2024, «Editorial: Forecasting in sports» 2019 | https://www.liverpool.ac.uk/people/ian-mchale | «Ian's research interests lie in statistics in sport and the analysis of gambling markets and issues relating to gambling. … serves as Associate Editor of the International Journal of Forecasting and the Journal of Quantitative Analysis in Sport.» | 2026-10-26 | 3-10, 3-14 |
| L. de Angelis — «University of Bologna, Italy» [WF] | CV на unibo.it: «Associate Professor in Econometrics at the Department of Economics of the University of Bologna». Работы в IJF: «Efficiency of online football betting markets» (2019, doi:10.1016/j.ijforecast.2018.07.008); «Informational efficiency and behaviour within in-play prediction markets» (2022, doi:10.1016/j.ijforecast.2021.05.012) | https://www.unibo.it/sitoweb/l.deangelis/cv-en | «G. Angelini, L. De Angelis - “Detection of biases in football exchange betting markets”, Reading Football Economics Workshop 2019» / «“Informational efficiency and price reaction within in-play prediction markets”» | 2026-10-26 | 3-11, 3-14 |
| S. Lessman — «Humboldt-Universität zu Berlin, Germany» [WF] (так написано на странице IJF) | Статья в IJF 2010 о скачках и ставках; по Crossref также EJOR 2009 о прогнозе скачек. Официальный профиль HU открыть не удалось (страница Anubis «Access Denied») | https://ideas.repec.org/a/eee/intfor/v26yi3p518-536.html | «Alternative methods of predicting competitive events: An application in horserace betting markets» / «Lessmann, Stefan & Sung, Ming-Chien & Johnson, Johnnie E.V.» / «International Journal of Forecasting» | 2026-10-26 | 3-12, 3-14 |
| M. Schienle — «Karlsruhe Institute of Technology, Germany» [WF] | В скрининге найдена одна работа о спорте, JQAS 2024 | https://api.crossref.org/works/10.1515/jqas-2023-0026 | «Success factors in national team football: an analysis of the UEFA EURO 2020» / «Melanie Schienle — Institute of Statistics, 150232 Karlsruhe Institute of Technology, Karlsruhe, Germany» | 2026-10-26 | 3-13 |
| M. Stegmaier — «University of Missouri, USA» [WF] | Проверен профиль. Тема — выборы. Слов sport / betting / prediction market на странице нет | https://truman.missouri.edu/people/stegmaier | «Dr. Stegmaier’s research concentrates on elections and voting behavior in the U.S. and Europe» | 2026-10-26 | 3-15 |
| F. Ziel, M. Oskarsdottir | Профили проверены: https://dsee.wiwi.uni-due.de/team/florian-ziel/ и https://www.southampton.ac.uk/people/668l6v/doctor-maria-oskarsdottir. Совпадений по sport / betting / gambling / football / tennis / prediction market нет. Единственное попадание подстроки «sport» на странице Ziel — слово «Vergleichsportalen» в названии бакалаврской работы | см. URL | — | 2026-10-26 | — |

Отброшенные совпадения скрининга B. Это однофамильцы: имя или область в записи Crossref не совпадают с членом редакции. Например: «David T. Hendry» (спортивная психология) против D.F. Hendry; «Rui J.B. Bessa» (зоотехния) против R.J. Bessa (INESC TEC); «Juan A./Juan F. Ortega»; «Roger C. Harris»; «Lisa Ferrara»; «Fengling Li / Feng Li»; «Xiaobo/Xuhan Yang»; «Hai Li»; «Michael A. Seifert»; «Shiyan Sheng»; «Min-Hye Shin»; «Joshua Castle»; несколько «Yang» против Yangzhuoran Fin Yang. Полный список: `3-14`.

---

## 4. Ссылки, которые не удалось подтвердить

### 4A. Clinton & Huang

| Что проверяли | Результат | URL | Цитата | Дата | Файл |
|---|---|---|---|---|---|
| Где выложена | **SocArXiv** (OSF Preprints, provider `socarxiv`), идентификатор **d5yx2**. HTML-страница osf.io отдаёт 403, данные взяты из API OSF | https://osf.io/preprints/socarxiv/d5yx2_v5/ ; API: https://api.osf.io/v2/preprints/d5yx2/ | `"provider": {"data": {"id": "socarxiv"}}` | 2026-10-26 | 4-01 |
| Авторы | Joshua Clinton, TzuFeng Huang (contributors в OSF). Аффилиация в OSF не указана: список institutions пуст | https://api.osf.io/v2/preprints/d5yx2_v5/contributors/ | «Joshua Clinton», «TzuFeng Huang» | 2026-10-26 | 4-01 |
| Название текущей (последней) версии v5 | «Prediction Markets? The Accuracy and Efficiency of Political Prediction Markets in the 2024 Presidential Election» | https://api.osf.io/v2/preprints/d5yx2/ | `"version": 5`, `"is_latest_version": true` | 2026-10-26 | 4-01 |
| Название версий v1–v3 | «Prediction Markets? The Accuracy and Efficiency of $2.4 Billion in the 2024 Presidential Election» | https://api.osf.io/v2/preprints/d5yx2_v5/versions/ | — | 2026-10-26 | 4-01 |
| Даты версий (date_published, UTC) | v1: 2025-12-01T21:32:31 (создана 2025-12-01T15:44:08); v2: 2025-12-08T02:09:02 (создана 2025-12-06T22:53:32); v3: 2025-12-09T21:42:09; **v4: API отвечает 403**, в списке версий её нет; **v5: 2026-06-10T19:31:38** (создана 2026-06-10T16:10:39, `date_modified` 2026-06-10T20:03:01) | https://api.osf.io/v2/preprints/d5yx2_v5/versions/ ; https://api.osf.io/v2/preprints/d5yx2_v4/ | — | 2026-10-26 | 4-01 |
| DOI / номер | v5: **10.31235/osf.io/d5yx2_v5**; v1: 10.31235/osf.io/d5yx2_v1. Оба резолвятся на osf.io (302) | https://doi.org/10.31235/osf.io/d5yx2_v5 | `"preprint_doi": "https://doi.org/10.31235/osf.io/d5yx2_v5"` | 2026-10-26 | 4-01 |
| Год | Первая версия 2025, последняя 2026 (см. даты) | — | — | 2026-10-26 | 4-01 |
| Лицензия препринта | CC0 1.0 Universal (license record в OSF) | https://api.osf.io/v2/preprints/d5yx2_v5/?embed=license | «CC0 1.0 Universal» | 2026-10-26 | — |
| Аннотация v5 (начало) | — | https://api.osf.io/v2/preprints/d5yx2/ | «Nearly 2,200 political prediction markets involving more than $3.2 billion in platform-reported trading volume (Confino, 2024) were traded across the Iowa Electronic Markets, Kalshi, PredictIt, and Polymarket during the final nine weeks of the 2024 U.S. presidential campaign.» | 2026-10-26 | 4-01 |
| Аннотация v1 (фрагмент) | — | https://api.osf.io/v2/preprints/d5yx2_v1/ | «We analyze more than 2,500 political prediction markets traded across the Iowa Electronic Markets, Kalshi, PredictIt, and Polymarket during the final five weeks of the 2024 U.S. presidential campaign…» | 2026-10-26 | 4-01 |
| SSRN | **Не найдено.** papers.ssrn.com отвечает 403 (Cloudflare). В поисковой выдаче SSRN-версии нет [WS] | — | — | 2026-10-26 | — |
| Сайт автора | **Не проверялся / не найден** | — | — | 2026-10-26 | — |

### 4B. Clegg & Cartlidge, arXiv:2510.20454

| Что проверяли | Результат | URL | Цитата | Дата | Файл |
|---|---|---|---|---|---|
| История версий | Две версии: v1 и v2. Адрес v3 отдаёт 404 | https://arxiv.org/abs/2510.20454 | «[v1] Thu, 23 Oct 2025 11:41:45 UTC (1,240 KB)» / «[v2] Thu, 18 Jun 2026 15:08:42 UTC (1,690 KB)» | 2026-10-26 | 4-04 |
| Название v1 | «Intransitive Player Dominance and Market Inefficiency in Tennis Forecasting: A Graph Neural Network Approach» (Lawrence Clegg, John Cartlidge). Comments: «39 pages, 8 figures» | https://arxiv.org/abs/2510.20454v1 | Из аннотации v1: «we achieve significant positive returns of 3.26% ROI with Kelly staking over 1903 bets» | 2026-10-26 | 4-03 |
| Название v2 | «Capturing Intransitive Dominance in Tennis Forecasting: A Graph Neural Network Approach» (Lawrence Clegg, John Cartlidge) | https://arxiv.org/abs/2510.20454v2 | Comments: «41 pages, 7 figures. Major revision reframing the paper from betting-market inefficiency toward intransitivity analysis, forecast complementarity, and robustness. Added forecast-encompassing tests, new intransitivity measures, robustness analyses, and expanded appendices» | 2026-10-26 | 4-04 |
| Есть ли в тексте v2 доходность против Pinnacle (ROI, Kelly, returns) | Поиск по полному тексту PDF v2 (41 стр.). «ROI» — 0, «Kelly» — 0, «returns» — 0, «return on investment» — 0, «staking» — 0, «bankroll» — 0. «profit» — 1, только в названии работы из списка литературы (van Ours 2025, «…A profitable anomaly»). «stake» — 1, только в ссылке («High Stakes, London»). «Pinnacle» — 11, везде как эталон для сравнения по вероятностям и Brier score | https://arxiv.org/pdf/2510.20454v2 | p.19: «For the bookmaker benchmark, we derive margin-adjusted implied probabilities from Pinnacle Sports odds using the model of Shin (1993)» / p.20: «The bookmaker odds’ implied probability, denoted as “PS”, remains notably superior overall with 68.7% accuracy and 0.198 Brier score» / p.25: «The market itself encompasses our model: adding πG to recalibrated Pinnacle gives no Brier-score improvement on either intransitivity subset (DM p ≥ 0.47)» / p.28: «combining it with Pinnacle’s odds yields no measurable Brier-score improvement» | 2026-10-26 | 4-05 |

Аннотация v2 (с той же страницы): «Our model (65.7% accuracy, 0.214 Brier score) forecasts competitively with established rating systems such as Weighted Elo.» Полный PDF в папку не сохранён. Сохранены страницы abs обеих версий и выписка результатов поиска с номерами страниц (`4-05`).

---

## 5. Условия использования данных

### 5A. Polymarket

| Что проверяли | Результат | URL | Цитата | Дата | Файл |
|---|---|---|---|---|---|
| Где лежит Terms of Use | На странице polymarket.com/tos текст встроен как Google Doc (iframe). Документ экспортирован в PDF (19 страниц) | https://polymarket.com/tos → https://docs.google.com/document/d/1N4aYlRcqaWCeKMID7vUSWJ1UPMvw_v6SP4cOFN8ZxR4/preview | «POLYMARKET.COM TERMS OF USE Effective as of August 11, 2026». Сторона договора: «Adventure One QSS, Inc. (the “Company,” “A1” “we,” “us,” or “our”)» | 2026-10-26 | 5-01, 5-02 |
| Распространяется ли ToS на доступ через API | Да, это сказано в преамбуле (NOTICE) | там же | «BY ACCESSING, INTERACTING WITH OR USING THE SITE, ANY FEATURE OR ANY OTHER INTERFACE (INCLUDING BY CONNECTING VIA AN API, …), … AGREE TO BE BOUND BY THE TERMS» | 2026-10-26 | 5-01 |
| Запреты на сбор и копирование. Раздел 4 «Your Responsibilities, Representations & Prohibited Conduct», подраздел 2 «Your Responsibilities & Prohibited Conduct» (PDF, с. 7–9) | В списке «You agree that you will not:» | там же | с. 8: «Harvest or otherwise collect information from the Site, any other Interface, or the Features for any unauthorized purpose;» / с. 9: «Use any data mining tools, robots, crawlers, or similar data gathering and extraction tools to scrape or otherwise remove data from the Site, any other Interface, or Features;» / с. 9: «Use any manual process to monitor or copy any of the material on the Site, any other Interface, or Features or for any other unauthorized purpose without our prior written consent;» | 2026-10-26 | 5-01 |
| Распространение данных (Data). Тот же подраздел (PDF, с. 9) | Определение «Data» и запрет перепродажи и распространения для Capital Market Client и market data distributor | там же | «Access or use any data, content, or information contained on our Site, any Interface or Features directly or through an API, or any other means, including on-chain, whether in raw, derived, aggregated, or anonymized form (the “Data”) if you are (i) a non-retail, professional entity that engages in capital markets activities … (each, a “Capital Market Client”), or (ii) a market data distributor, in each case unless otherwise agreed to in writing by us;» / «Sell, resell, sublicense, redistribute, or otherwise commercially exploit the Data to any Capital Market Client or market data distributor, unless otherwise agreed to in writing by us;» | 2026-10-26 | 5-01 |
| Права и лицензия. Раздел 5 «Intellectual Property Rights», подраздел 1 «Ownership & License» (PDF, с. 10–11) | — | там же | «The Company, Blockratize or its licensors own all right, title, and interest, including all intellectual property rights, in and to the Site, any other Interface, and Features, including any related content and technology, unless otherwise indicated. Subject to the Terms, the Company hereby grants you a personal, limited, revocable, non-exclusive, non-sublicensable, non-transferable license to use, copy, and distribute in connection with such use the Site, any other Interface, and Features. This license is solely intended to allow you to access, use or otherwise interact with the Site, any other Interface, and Features.» | 2026-10-26 | 5-01 |
| Характер информации. Раздел 2.2 (PDF, с. 3) | — | там же | «all information provided as part of the Content Features in connection with your access and use of the Site is intended for informational purposes only.» | 2026-10-26 | 5-01 |
| Отдельные условия API (Gamma, CLOB) | Отдельной страницы с условиями API **не найдено**. В sitemap документации 544 URL, ни один не содержит term / legal / licen / polic / tos. В llms-full.txt «Terms of Service» встречается только в разделах про программы (rewards, rebates, referrals) | https://docs.polymarket.com/sitemap.xml ; https://docs.polymarket.com/llms-full.txt | — | 2026-10-26 | 5-05 |
| Обзор API в документации | Описаны Gamma API и CLOB API | https://docs.polymarket.com/api-reference/predictions/overview | «Gamma API … https://gamma-api.polymarket.com … Discover events and markets, and retrieve the metadata needed to work with them.» / «CLOB API … https://clob.polymarket.com … Read live market state, then place and manage orders.» | 2026-10-26 | 5-03 |
| Лимиты запросов | Лимиты по IP через Cloudflare | https://docs.polymarket.com/api-reference/rate-limits | «Cloudflare IP-based request limits for Polymarket APIs» / Gamma: «General \| 4,000 req / 10s» | 2026-10-26 | 5-04 |
| Поле license в OpenAPI-спецификациях | В CLOB-спецификации и в Data API v2 указано `license: MIT`. В Gamma-спецификации поля license нет. Data API v2: «Auth: none» | https://docs.polymarket.com/api-spec/clob-openapi.yaml ; https://docs.polymarket.com/api-spec/gamma-openapi.yaml ; https://data-api.polymarket.com/v2/openapi.json | «license: name: MIT identifier: MIT» (CLOB) / «**Auth**: none. All data routes are public; no API key or token is required.» (Data API v2) | 2026-10-26 | 5-05 |

### 5B. tennis-data.co.uk

| Что проверяли | Результат | URL | Цитата | Дата | Файл |
|---|---|---|---|---|---|
| Условия использования и распространения | **Не удалось открыть.** Главная, alldata.php и notes.txt отдают 403 (Cloudflare) для curl, Chromium и WebFetch. В поиске по запросу об условиях tennis-data.co.uk страниц самого сайта нет [WS] | http://www.tennis-data.co.uk/ | Блок-страница: «Sorry, you have been blocked You are unable to access tennis-data.co.uk» | 2026-10-26 | 5-06 |

### 5C. Jeff Sackmann, tennis_atp и tennis_wta

| Что проверяли | Результат | URL | Цитата | Дата | Файл |
|---|---|---|---|---|---|
| Открыты ли репозитории сейчас | **Нет, не открыты.** github.com отдаёт 404 на оба (WebFetch; контрольный запрос к другому репозиторию проходит). Все проверенные raw-файлы (README.md, LICENSE, *_players.csv; ветки master, main, HEAD) — 404, а контрольный raw-файл tennis_MatchChartingProject — 200. В профиле JeffSackmann виден один публичный репозиторий | https://github.com/JeffSackmann/tennis_atp ; https://github.com/JeffSackmann/tennis_wta ; https://github.com/JeffSackmann | «The server returned HTTP 404 Not Found.» [WF] / профиль: «The page shows one public repository … tennis_MatchChartingProject» [WF] | 2026-10-26 | 5-07 |
| Сторонние сообщения об удалении (не официальные) | Issue от 20 сентября 2026 года: удалены четыре репозитория | https://github.com/MLT-OSS/FirstData/issues/238 | «Four repositories from that account were removed» / «`tennis_atp`, `tennis_wta`, `tennis_pointbypoint` and `tennis_slam_pointbypoint`» / «Verified 2026-09-20.» [WF] | 2026-10-26 | 5-11 |
| Лицензия (по копии README из исходных репозиториев) | **CC BY-NC-SA 4.0** — так сказано в копиях README, сохранённых в стороннем зеркале. Официальный текст в самих репозиториях сейчас недоступен | https://raw.githubusercontent.com/Aneeshers/tennis-sackmann-archive/main/atp/UPSTREAM_README.md ; …/wta/UPSTREAM_README.md | «Tennis databases, files, and algorithms by Jeff Sackmann / Tennis Abstract is licensed under a Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License.» / «In other words: Attribution is required. Non-commercial use only.» | 2026-10-26 | 5-09, 5-10 |
| Стороннее зеркало | Архивная копия с той же лицензией. Снимки atp и wta сделаны из исходных коммитов июня 2026 года (по словам автора зеркала) | https://raw.githubusercontent.com/Aneeshers/tennis-sackmann-archive/main/README.md | «the `atp` and `wta` snapshots from upstream commits made in June 2026.» / «redistributed under the same license he releases it under: Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International (CC BY-NC-SA 4.0)» | 2026-10-26 | 5-08 |

---

## 6. arXiv

| Что проверяли | Результат | URL | Цитата | Дата | Файл |
|---|---|---|---|---|---|
| Поиск на arxiv.org по названию | **Не найдено** | https://arxiv.org/search/?query=%22Model+Edge+or+Model+Miscalibration%22&searchtype=title | «Sorry, your query for title: "Model Edge or Model Miscalibration" produced no results.» | 2026-10-26 | 6-01 |
| arXiv API по названию | **Не найдено** | https://export.arxiv.org/api/query?search_query=ti:%22Model%20Edge%20or%20Model%20Miscalibration%22 | `<opensearch:totalResults>0` | 2026-10-26 | 6-04 |
| Дополнительные запросы | Пусто по всем: title «prospective test Polymarket», «Model Miscalibration tennis», «tennis prediction market»; abstract «Polymarket tennis», «Miscalibration Polymarket»; all-fields «Polymarket tennis»; API `abs:Polymarket AND abs:tennis` | arxiv.org/search | «Sorry, your query … produced no results.» | 2026-10-26 | — |
| Работает ли поиск (контроль) | По «Polymarket» (все поля) 66 результатов, самый свежий 2610.30488 от 21 октября 2026. В названиях и аннотациях этих 66 записей слова «tennis» нет | https://arxiv.org/search/?query=Polymarket&searchtype=all | «Showing 1–50 of 66 results for all: Polymarket» | 2026-10-26 | 6-02, 6-03 |

---

## Что не нашлось или не удалось проверить

1. **IJF Guide for Authors (ScienceDirect)** не открылся: 403 для curl, Chromium и WebFetch; Wayback и archive.ph тоже недоступны. Поэтому по самому Guide не подтверждены: лимит аннотации, число keywords, требования к highlights для IJF, title page, анонимизация метаданных, лимит длины, фигуры и подписи, таблицы, заголовок и место раздела про GenAI именно в IJF, competing interests и funding, DOI в ссылках. Где искал: sciencedirect.com, elsevier.com/journals/…/guide-for-authors (редирект на ScienceDirect), Editorial Manager (ссылка ведёт туда же), shop.elsevier.com, forecasters.org/ijf/*, web.archive.org, archive.ph, WebSearch.
2. **Файл «Guidelines for IJF submissions»** по ссылке со страницы IJF (https://pierrepinson.com/IJF/IJFauthorguidelines.pdf) отдаёт 404.
3. **Лимит длины статьи** и **требование к редактируемым таблицам** не найдены нигде из доступного.
4. **Требование DOI в ссылках** не найдено.
5. **Редакционная статья 10.1016/j.ijforecast.2026.08.004**: полного текста нет (не в открытом доступе, ScienceDirect 403), аннотации нет ни в Crossref, ни в Semantic Scholar, ни в Elsevier API.
6. **Формат пакета воспроизводимости**: на странице IJF не упоминается [WF], в других доступных источниках не найден.
7. **Новость Cardiff University** о Reproducibility Editor: 403. Сведения о CASCaD есть только в поисковой выдаче [WS] и не проверены.
8. **Почта Erik Štrumbelj** на официальной странице FRI не указана, там форма «Send a message». COBISS/SICRIS: страница Anubis «Access Denied».
9. **Должность Gustav Šír** на странице FEL ČVUT не указана.
10. **Официальный профиль S. Lessmann** на HU Berlin: страница Anubis «Access Denied». Использована запись о публикации на IDEAS/RePEc.
11. **Clinton & Huang**: SSRN-версия не найдена (SSRN 403, в выдаче нет). Сайт автора не проверен. Версия v4 на OSF закрыта (403). HTML-страница osf.io: 403, использован API.
12. **tennis-data.co.uk**: условия использования не прочитаны, сайт отдаёт 403 всеми способами.
13. **Sackmann tennis_atp / tennis_wta**: текущую лицензию в самих репозиториях проверить нельзя, они недоступны (404). Лицензия взята из копий README в стороннем зеркале.
14. **Отдельные условия API Polymarket** (Gamma, CLOB) не найдены в документации. Есть только общий ToS, который распространяется и на доступ через API.
15. **Статья «Model Edge or Model Miscalibration? A prospective test on Polymarket tennis»** в arXiv не найдена.
16. **Страницы forecasters.org/ijf/*** (For authors, Keywords, Editors, главная) прочитаны только через WebFetch. Цитаты оттуда (метка [WF]) не сверены с сырым HTML.

## Файлы в папке

| Файл | Что это |
|---|---|
| 1-01_sciencedirect_guide_for_authors_403_block.html | Блок-страница ScienceDirect вместо Guide for Authors |
| 1-02_forecasters_ijf_authors_webfetch.md | Выдержка WebFetch со страницы IJF «For authors» и проверка ссылок с неё |
| 1-03_forecasters_ijf_keywords_webfetch.md | Выдержка WebFetch со страницы IJF Preferred Keywords |
| 1-04_ijf_latex_template_ijftemplate.tex | Официальный LaTeX-шаблон IJF, по ссылке со страницы «For authors» |
| 1-05_elsevier_shop_ijf_journal_page.html | Страница журнала на shop.elsevier.com |
| 1-06_editorialmanager_ijf_mainpage.html | Editorial Manager IJF, фрейм mainpage.html |
| 1-07_websearch_indirect_guide_for_authors.md | Пересказ поисковой выдачи по Guide for Authors [WS] |
| 1-08_elsevier_generic_highlights.html | Общая страница Elsevier про Highlights |
| 1-09_elsevier_generic_genai_policy.html | Общая политика Elsevier по GenAI |
| 2-01_forecasters_ijf_home_webfetch.md | Политика data/code и воспроизводимости на главной IJF (WebFetch) |
| 2-02_editorial_ijforecast.2026.08.004_metadata.json | Метаданные редакционной статьи: Crossref, Elsevier API, Semantic Scholar |
| 2-03_cardiff_news_403_and_websearch_indirect.md | Новость Cardiff: журнал попыток и пересказ выдачи [WS] |
| 3-01 … 3-08 | Официальные страницы рецензентов |
| 3-09_forecasters_ijf_editors_webfetch.md | Список редакции IJF (WebFetch) |
| 3-10 … 3-13, 3-15 | Профили и записи публикаций членов редакции |
| 3-14_board_crossref_screen.json | Скрининг редакции по Crossref: метод и сырые совпадения |
| 4-01_socarxiv_d5yx2_osf_api.json | OSF API: метаданные, версии, авторы (Clinton & Huang) |
| 4-03, 4-04 | arXiv abs v1 и v2 (2510.20454) |
| 4-05_arxiv_2510.20454v2_fulltext_search.txt | Поиск по полному тексту v2 с номерами страниц |
| 5-01_polymarket_terms_of_use_gdoc_export.pdf | Polymarket Terms of Use (PDF-экспорт Google Doc) |
| 5-02 … 5-05 | polymarket.com/tos, документация API, лимиты, OpenAPI info |
| 5-06_tennis-data_co_uk_cloudflare_block.html | Блок-страница tennis-data.co.uk |
| 5-07_sackmann_github_access_log.md | Журнал проверок доступности репозиториев Sackmann |
| 5-08 … 5-10 | README стороннего зеркала и сохранённые им README из исходных репозиториев |
| 5-11_firstdata_issue238_webfetch.md | Стороннее issue об удалении репозиториев |
| 6-01 … 6-04 | Поиск arXiv: по названию, контрольный листинг «Polymarket», API |
