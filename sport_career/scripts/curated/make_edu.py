# -*- coding: utf-8 -*-
"""Ручные данные v2: строки с источниками (ссылка + дата). Правь здесь и перезапускай, затем build_xlsx_v2.py."""
import os as _os
BASE = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))) + "/"
import csv, sys
sys.path.insert(0,BASE)
import match_alumni as M
D=BASE+'data/'
alum=list(csv.DictReader(open(D+'v2/hse_insport_alumni.csv',encoding='utf-8')))
teach=list(csv.DictReader(open(D+'v2/hse_insport_teachers.csv',encoding='utf-8-sig')))
dpo=[('Наиль Измайлов','спикер'),('Алексей Сорокин','спикер'),('Вероника Логинова','спикер'),('Александр Чеботарев','руководитель программы')]
people=[]
for r in csv.DictReader(open(D+'v2/people_v2.csv',encoding='utf-8-sig')):
    if r['name'] not in ('—',''): people.append(('v2 Люди',r['org'],r['name'],r['role']))
for r in csv.DictReader(open(D+'people.csv',encoding='utf-8-sig')):
    if r['name'] not in ('—',''): people.append(('v1 Люди',r['org'],r['name'],r['role']))
def best(name, pool, key):
    kv=M.key_variants(name); out=None
    for p in pool:
        sc,kind=M.score(kv,M.key_variants(p[key]))
        if sc>=93 and (out is None or sc>out[0]): out=(sc,kind,p)
    return out
rows=[]; seen=set()
for sheet,org,name,role in people:
    if (name,org) in seen: continue
    seen.add((name,org))
    link,what,url,date="нет данных","Совпадений в списках выпускников и преподавателей магистратуры ВШЭ по спортменеджменту, спикеров ДПО ВШЭ и найденных историй РЭШ нет","",""
    a=best(name,alum,'name')
    if a:
        link="ВШЭ"; what=f"Выпускник(ца) магистратуры «Международный спортивный менеджмент, маркетинг и право», выпуск {a[2]['year']}; на странице указано: {a[2]['org']}"; url="https://www.hse.ru/ma/insport/alumni"; date="проверено 2026-11-04"
    t=best(name,teach,'name')
    if t:
        link="ВШЭ"; what=f"Преподает на магистерской программе ВШЭ по спортменеджменту: {t[2]['position'][:120]}"; url="https://www.hse.ru/ma/insport/teachers"; date="проверено 2026-11-04"
    for dn,drole in dpo:
        if M.score(M.key_variants(name),M.key_variants(dn))[0]>=93:
            link="ВШЭ"; what=f"{drole.capitalize()} программы ДПО ВШЭ «Руководитель спортивной организации» (старт 30.11.2026)"; url="https://www.hse.ru/edu/dpo/1140095287"; date="проверено 2026-11-04"
    if name=="Дмитрий Дагаев":
        link="РЭШ"; what="Магистратура РЭШ «Экономика» (2008); читает матанализ на совбаке ВШЭ–РЭШ; через его лабораторию выпускница BAE’20 вошла в футбол"; url="https://www.hse.ru/staff/ddagaev"; date="проверено 2026-11-04"
    if name=="Мария Котикова":
        link="РЭШ"; what="Выпускница совместного бакалавриата РЭШ и ВШЭ (BAE’20), история на сайте РЭШ; текущую должность свежим источником не подтвердил"; url="https://news.nes.ru/news/v-futbolnyij-klub-s-diplomom-ekonomista.-istoriya-marii-kotikovoj/"; date="дата публикации не указана"
    if name=="Ирина Лебедева":
        link="ВШЭ"; what="Выступала в ВШЭ на «Дне ФК «Зенит» (вместе с Кириллом Латой), рассказывала о футбольном маркетинге и карьере в клубе"; url="https://www.hse.ru/news/1055217481.html"; date="2025-06-09"
    rows.append(dict(sheet=sheet,org=org,name=name,role=role,link=link,what=what,url=url,source_date=date))
# дополнительно найденные связи (люди не из листов)
extra=[
 ("skip","НИУ ВШЭ, Лаборатория исследований спорта","Дмитрий Дагаев","Руководит научными и прикладными проектами Научно-учебной лаборатории исследований спорта","РЭШ","Магистратура РЭШ «Экономика» (2008); читает матанализ на совбаке ВШЭ–РЭШ; через его лабораторию выпускница BAE’20 вошла в футбол","https://www.hse.ru/staff/ddagaev","проверено 2026-11-04"),
 ("skip","ФК «Велес»","Мария Котикова","Матч-менеджер, по ее словам выходила на должность коммерческого директора и привела первого спонсора","РЭШ","Выпускница совместного бакалавриата РЭШ и ВШЭ (BAE’20), история на сайте РЭШ; текущую должность свежим источником не подтвердил","https://news.nes.ru/news/v-futbolnyij-klub-s-diplomom-ekonomista.-istoriya-marii-kotikovoj/","дата публикации не указана"),
 ("дополнительно","ФК «Зенит»","Кирилл Лата","Советник председателя правления по международным вопросам","ВШЭ","Выступал в ВШЭ на «Дне ФК «Зенит» вместе с Ириной Лебедевой","https://www.hse.ru/news/1055217481.html","2025-06-09"),
 ("дополнительно","Федерация падела России","Алексей Сорокин","Генеральный директор (по странице ДПО ВШЭ); ранее гендиректор оргкомитета ЧМ-2018","ВШЭ","Преподаватель магистерской программы и спикер ДПО ВШЭ по спортменеджменту","https://www.hse.ru/ma/insport/teachers","проверено 2026-11-04"),
 ("дополнительно","РПЛ (в прошлом)","Евгений Савин","Директор по проведению соревнований РПЛ до 2021 (по странице программы)","ВШЭ","Преподаватель магистерской программы ВШЭ по спортменеджменту (по отзывам выпускников, ведет футбольный блок)","https://www.hse.ru/ma/insport/teachers","проверено 2026-11-04"),
 ("дополнительно","ВШЭ, магистратура «Международный спортивный менеджмент»","Партнеры программы: РПЛ, ФНЛ, ФК «Спартак», «Локомотив», «Лужники», ВТБ Арена Парк и др.","—","ВШЭ","Организации-партнеры программы: удобный повод для знакомства через программу","https://www.hse.ru/ma/insport/ourpartners","проверено 2026-11-04"),
]
for e in extra:
    if e[0]=="skip": continue
    rows.append(dict(sheet=e[0],org=e[1],name=e[2],role=e[3],link=e[4],what=e[5],url=e[6],source_date=e[7]))
rows.sort(key=lambda r:({'РЭШ':0,'ВШЭ':1}.get(r['link'],2), r['sheet'], r['org']))
with open(D+'v2/edu_links.csv','w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
import collections
print(len(rows), collections.Counter(r['link'] for r in rows))
for r in rows:
    if r['link']!='нет данных': print(r['link'],'|',r['name'],'|',r['org'],'|',r['what'][:90])
