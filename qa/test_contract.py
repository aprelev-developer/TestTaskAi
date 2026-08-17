#!/usr/bin/env python3
"""Автотест контракта блога blog-platform.

Запуск:  python3 qa/test_contract.py
Зависимости: только стандартная библиотека Python 3 (см. AGENTS.md, "Стек и версии").

Тест проверяет поведение стенда http://localhost:8080 против ожиданий,
записанных в SPEC.md 9 ДО прогона. Часть проверок заведомо красная - они
закрывают BUG-001, BUG-002 и BUG-003. Зелёный тест, ничего не проверяющий,
курс не засчитывает, поэтому падения здесь ожидаемы и являются результатом.

Код возврата: 0 - все проверки прошли, 1 - есть падения, 2 - стенд недоступен.
"""

import re
import sys
import urllib.error
import urllib.request

BASE = "http://localhost:8080"
TIMEOUT = 10

results = []


def request(path, method="GET"):
    """Возвращает (код ответа, тело). Сетевые ошибки не глушим - стенд обязан быть поднят."""
    req = urllib.request.Request(
        BASE + path, headers={"User-Agent": "qa-contract-test"}, method=method
    )
    try:
        resp = urllib.request.urlopen(req, timeout=TIMEOUT)
        return resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", "replace")


def post_ids(html):
    """Идентификаторы постов в порядке отрисовки карточек."""
    return [int(m) for m in re.findall(r'post-card__title">\s*<a href="/post/(\d+)"', html)]


def check(test_id, description, passed, detail):
    results.append((test_id, description, passed, detail))


# --- T01, T02, T05: базовые сценарии ------------------------------------

status, html = request("/")
check("T01", "GET / отдаёт 200", status == 200, f"код {status}")
check(
    "T01b",
    "на главной есть все 6 категорий",
    len(set(re.findall(r"/category/([a-z]+)", html))) == 6,
    f"найдено {len(set(re.findall(r'/category/([a-z]+)', html)))}",
)

status, html = request("/category/programming")
programming_ids = post_ids(html)
check("T02", "GET /category/programming отдаёт 200", status == 200, f"код {status}")
check("T02b", "в категории programming есть посты", len(programming_ids) > 0,
      f"{len(programming_ids)} постов")

status, post4 = request("/post/4")
check("T05", "GET /post/4 отдаёт 200", status == 200, f"код {status}")

# T05c добавлена по итогам аудита (A-5): ожидание T05 в SPEC.md 9 говорит
# "категории поста отображены" во множественном числе, и в SPEC.md 5 сценарий 3
# - "принадлежность к категориям". Пост 4 состоит в двух категориях, а его
# страница объявляет одну. Это BUG-004.
listed_in = []
for slug in ("design", "programming", "technology", "business", "science", "lifestyle"):
    _, listing = request(f"/category/{slug}")
    if 'href="/post/4"' in listing:
        listed_in.append(slug)
shown_on_page = sorted(set(re.findall(r'href="/category/([a-z]+)"', post4)))
check(
    "T05c",
    "BUG-004: страница поста показывает все категории, в листингах которых он есть",
    sorted(listed_in) == shown_on_page,
    f"в листингах {sorted(listed_in)}, на странице поста {shown_on_page}",
)


# --- T04: сортировка ----------------------------------------------------

_, html = request("/category/programming?sort=title")
titles = re.findall(r'post-card__title">\s*<a href="/post/\d+">(.*?)</a>', html, re.S)
titles = [t.strip() for t in titles]
check(
    "T04",
    "sort=title сортирует по заголовку без учёта регистра",
    titles == sorted(titles, key=str.lower),
    f"порядок: {titles[:3]}...",
)


# --- T06, T07, T08: несуществующие ресурсы ------------------------------

status, _ = request("/category/nonexistent")
check("T06", "несуществующая категория отдаёт 404", status == 404, f"код {status}")

status, _ = request("/post/999999")
check("T07", "несуществующий пост отдаёт 404", status == 404, f"код {status}")

status, body = request("/post/abc")
check("T08", "нечисловой id отдаёт 404 или 400, не 5xx", status in (400, 404), f"код {status}")
check(
    "T08b",
    "трассировка стека наружу не уходит",
    "Stack trace" not in body and "#0 " not in body,
    "трассировки нет" if "Stack trace" not in body else "НАЙДЕНА трассировка",
)


# --- T11: неизвестное значение sort -------------------------------------

status, _ = request("/category/programming?sort=hacked")
check("T11", "неизвестный sort отклоняется с 400", status == 400, f"код {status}")

status, _ = request("/category/programming?sort=title'--")
check("T11b", "sort с кавычкой не ломает запрос", status == 400, f"код {status}")


# --- T10 / BUG-001: согласованность валидации page ----------------------
# Ожидание из SPEC.md 9: одинаковая логика для всех некорректных значений.

page_codes = {}
for value in ["0", "-1", "abc", "1.5", "", "99999999999999999999"]:
    page_codes[value or "(пусто)"], _ = request(f"/category/programming?page={value}")

distinct = set(page_codes.values())
check(
    "T10",
    "BUG-001: все некорректные значения page обрабатываются одинаково",
    len(distinct) == 1,
    f"коды ответа: {page_codes}",
)

status, _ = request("/category/programming?page=99999999999999999999")
check(
    "T10b",
    "BUG-001: номер страницы за пределами int не выдаёт первую страницу",
    status != 200,
    f"код {status} (200 означает молчаливую подмену на страницу 1)",
)


# --- T09 / BUG-002: пустое состояние за пределами диапазона -------------

status, html = request("/category/programming?page=2")
check(
    "T09",
    "BUG-002: страница за диапазоном не утверждает, что категория пуста",
    "No posts found in this category" not in html,
    "на странице текст 'No posts found in this category', "
    f"хотя в категории {len(programming_ids)} постов",
)
# Проверка «на странице есть элементы пагинации» СНЯТА по итогам аудита (A-7).
# Причина: perPage = 9, а максимум постов в категории — 8, поэтому шаблон
# pagination.tpl штатно не отрисовывается при {if $pagination->totalPages > 1}.
# Отсутствие контролов здесь — следствие данных, а не дефект. Держать это
# падающей проверкой значило бы нарушить SPEC.md §10, U5, где я обязался
# фиксировать такое как наблюдение, а не трактовать самостоятельно.


# --- BUG-003: метод HEAD ------------------------------------------------

status, _ = request("/", method="HEAD")
check("B003", "BUG-003: HEAD / отдаёт 200, как требует RFC 9110", status == 200, f"код {status}")

status, _ = request("/post/4", method="HEAD")
check("B003b", "BUG-003: HEAD /post/4 отдаёт 200", status == 200, f"код {status}")


# --- вывод --------------------------------------------------------------

def main():
    try:
        request("/")
    except Exception as exc:  # стенд не поднят - это не падение теста, а отсутствие объекта
        print(f"СТЕНД НЕДОСТУПЕН: {BASE} — {exc!r}")
        print("Поднимите стенд по инструкции из README.md и повторите.")
        return 2

    failed = [r for r in results if not r[2]]
    print(f"Автотест контракта · стенд {BASE}")
    print("=" * 72)
    for test_id, description, passed, detail in results:
        mark = "OK  " if passed else "FAIL"
        print(f"[{mark}] {test_id:<6} {description}")
        if not passed:
            print(f"         └─ {detail}")
    print("=" * 72)
    print(f"Всего: {len(results)}   прошло: {len(results) - len(failed)}   упало: {len(failed)}")
    if failed:
        bug_by_test = {
            "T10": "BUG-001 (несогласованная валидация page)",
            "T10b": "BUG-001 (несогласованная валидация page)",
            "T09": "BUG-002 (ложное пустое состояние)",
            "T05c": "BUG-004 (показана одна категория из нескольких)",
            "B003": "BUG-003 (HEAD отдаёт 405)",
            "B003b": "BUG-003 (HEAD отдаёт 405)",
        }
        print("\nУпавшие проверки соответствуют записанным дефектам:")
        for test_id, _, _, _ in failed:
            print(f"  {test_id:<6} → {bug_by_test.get(test_id, 'дефект вне списка баг-репортов')}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
