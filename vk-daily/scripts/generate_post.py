"""Build one ~1800–2200 char Ufa story post + 4–8 word cover headline + description."""
from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Any

from validate_post import validate_description, validate_headline, validate_post, load_banned, load_tenant


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def pick_news(items: list[dict], today: date) -> dict:
    dated = []
    for item in items:
        try:
            d = date.fromisoformat(str(item["date"]))
        except (KeyError, ValueError):
            continue
        if d <= today:
            dated.append((d, item))
    if not dated:
        raise RuntimeError("news-bank has no item on or before today")
    dated.sort(key=lambda pair: pair[0], reverse=True)
    return dated[0][1]


def pick_composition(
    compositions: list[dict],
    seed: str,
    used: list[str],
    preferred_id: str = "",
) -> dict:
    if preferred_id:
        for c in compositions:
            if c.get("id") == preferred_id and c.get("id") not in used:
                return c
        for c in compositions:
            if c.get("id") == preferred_id:
                return c
    unused = [c for c in compositions if c.get("id") not in used]
    pool = unused or compositions
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    idx = int(digest, 16) % len(pool)
    return pool[idx]


def _headlines_and_deks_for(news: dict) -> list[tuple[str, str]]:
    angle = news.get("angle") or ""
    if angle == "utility_bills":
        return [
            ("Зима в городе: считаем платёж", "Проверь теплосчётчик до квитанции."),
            ("Как не переплатить за тепло зимой", "Проверь теплосчётчик до квитанции."),
            ("Проверь теплосчётчик до первой квитанции", "Как сохранить семейный бюджет этой зимой."),
            ("Готовим квартиру к счетам за отопление", "Проверь теплосчётчик до квитанции."),
        ]
    if angle == "home_repair":
        return [
            ("Как подготовить квартиру к зимним холодам", "Простые шаги против сквозняков и переплат."),
            ("Проверяем окна и радиаторы до осени", "Как сохранить тепло и деньги в Уфе."),
            ("Скрытые дефекты ремонта перед холодами", "Где уходит тепло в уфимских домах."),
        ]
    if angle == "family_budget":
        return [
            ("Считаем семейный бюджет по районам Уфы", "Дёма, Сипайлово или Инорс: где жить спокойнее."),
            ("Сколько стоит жизнь семьи в Уфе", "Коммуналка, дороги и садики без иллюзий."),
        ]
    default_h = news.get("default_headline") or "Зима в городе: считаем платёж"
    default_d = news.get("default_description") or "Проверь теплосчётчик до квитанции."
    return [(default_h, default_d)]


def pick_headline_and_description(news: dict, seed: str, tenant: dict) -> tuple[str, str]:
    pairs = _headlines_and_deks_for(news)
    digest = hashlib.sha256((seed + "|headline_dek").encode("utf-8")).hexdigest()
    ordered = [pairs[int(digest, 16) % len(pairs)]] + pairs
    for candidate_h, candidate_d in ordered:
        err_h = validate_headline(candidate_h, tenant)
        err_d = validate_description(candidate_d, tenant)
        if not err_h and not err_d:
            return candidate_h, candidate_d
    raise RuntimeError("no valid cover headline and description pair")


def _utility_bills_body(_news: dict) -> str:
    return """Каждую осень в Уфе повторяется один и тот же сценарий: в октябре включают батареи, а в ноябре полгорода хватается за голову от первой платежки за отопление. Счета от БашРТС и МУП УИС традиционно становятся самой увесистой строкой в расходах семьи. Но мало кто знает, что сумму в этой квитанции можно срезать на треть, если сделать пару простых шагов еще в сентябре, пока система стоит сухой.

Я Руслан Мухтаров, Самолет Плюс, Уфа. Когда мы с клиентами смотрим квартиры в Сипайлово, Дёме, Инорсе или Зеленой роще, я всегда первым делом смотрю не на цвет обоев, а в квитанции за прошлый февраль и на тепловой узел. Коммуналка в двух соседних одинаковых девятиэтажках может отличаться на четыре тысячи рублей в месяц. И дело тут не в магии, а в банальных приборах учета.

Если ваш дом сдан после 2012 года, у вас с высокой вероятностью есть индивидуальный поквартирный теплосчетчик. И здесь кроется главная ловушка сентября: межповерочный интервал. У большинства счетчиков он составляет от четырех до шести лет. Если срок поверки истек летом, а вы не обратили внимания, управляющая компания молча переведет квартиру на расчет по нормативу с повышающим коэффициентом. В результате за обычную двушку вместо трех тысяч рублей легко прилетит семь.

Что нужно сделать прямо сейчас, не откладывая на морозы:

Во-первых, откройте паспорт своего теплосчетчика в щитке на лестничной площадке или посмотрите дату последней поверки в личном кабинете ЕРКЦ. Если срок подошел к концу, вызовите поверителя на этой неделе. Это стоит полторы-две тысячи рублей, а экономит до пятнадцати тысяч за один зимний сезон. Главное, отнесите акт поверки в свою управляющую компанию до официального пуска тепла.

Во-вторых, проверьте регуляторы на радиаторах. Термостатические клапаны за лето часто закисают в открытом положении. Если их не расходить сейчас, зимой придется открывать окна настежь и отапливать уфимский воздух за собственные деньги.

Если вы только выбираете квартиру или готовите свою к продаже, напишите в сообщения сообщества. Проверим реальные коммунальные платежи по дому, оценим состояние коммуникаций и разложим цифры спокойно, без лишней суеты."""


def _home_repair_body(_news: dict) -> str:
    return """Осень в Уфе наступает стремительно, и главная проверка любого ремонта начинается с первыми заморозками. В Сипайлово с его ветрами с Белой или в панельных домах Черниковки сразу становится понятно, где мастера сэкономили на пене, а где оконная фурнитура просела за лето. Греть улицу за свой счет при нынешних тарифах на отопление удовольствие сомнительное.

Я Руслан Мухтаров, Самолет Плюс, Уфа. На осмотрах квартир перед сделкой я постоянно вижу одну картину: люди вложили миллион в плитку и ламинат, а зимой ходят в шерстяных носках, потому что из под подоконника дует, как из открытой форточки.

Проверить квартиру перед отопительным сезоном можно за двадцать минут своими руками. Возьмите обычный лист бумаги, прижмите его створкой пластикового окна и потяните. Если лист легко выскальзывает, прижим створки ослаб. Шестигранником переведите эксцентрики на торце створки в зимний режим, это займет пять минут на каждое окно.

Второй момент, радиаторы отопления. Пока воду в стояки не подали под давлением, проверьте краны Маевского и стыки труб. Если на соединениях есть следы ржавых подтеков с прошлой весны, при первом же гидравлическом ударе они потекут прямо на ваш свежий паркет. Заменить прокладку в сентябре стоит копейки, а устранять последствия залива соседей снизу выйдет в сотни тысяч рублей.

Третья точка риска, вентиляция на кухне и в санузле. В старых домах тяга часто опрокидывается, когда на улице холодает, и холодный воздух из вентиляционной шахты начинает задувать прямо в квартиру. Проверьте тягу тонкой салфеткой при приоткрытом окне.

Если планируете покупку жилья в Уфе или хотите проверить свой дом перед сделкой, напишите в сообщения сообщества. Помогу оценить техническое состояние без прикрас и сберечь семейный бюджет."""


def _family_budget_body(_news: dict) -> str:
    return """Когда семья в Уфе выбирает район для жизни, обычно сравнивают только стоимость самой квартиры. В Дёме квадрат кажется доступнее, в Сипайлово развитая инфраструктура, в Зеленой роще престиж и близость к центру. Но реальная стоимость жизни складывается не только из ежемесячного платежа банку. Коммуналка, транспортные расходы и время в пути каждый месяц забирают ощутимую часть заработка.

Я Руслан Мухтаров, Самолет Плюс, Уфа. Давайте посчитаем житейскую математику без рекламных буклетов. Если семья из трех человек берет жилье на выезде из города, разница в цене квартиры может составлять полтора-два миллиона рублей. Но к этой сумме сразу добавляются расходы на две машины, бензин по пробкам на мостах и постоянное обслуживание авто. За пять лет эти скрытые траты полностью съедают всю первоначальную выгоду.

Второй фактор, коммунальные платежи. В домах с собственной крышной котельной или поквартирным отоплением счета зимой в полтора-два раза ниже, чем в старых панельках с центральным отоплением от городских ТЭЦ. На дистанции в десять лет разница в коммуналке легко переваливает за полмиллиона рублей. Это деньги, которые вы могли бы потратить на отпуск или обучение детей, а не отдавать поставщикам ресурсов.

Третий момент, время. Дорога на работу и в школы через Бельский или Шакшинский мост в часы пик отнимает до двух часов ежедневно. Это время невозможно вернуть или компенсировать скидкой от застройщика.

Поэтому выбор района всегда должен начинаться с честного калькулятора всех расходов на пять лет вперед. Напишите в сообщения сообщества, если хотите подобрать квартиру в Уфе с учетом реального семейного бюджета и транспортной доступности."""


def _fit_length(text: str, min_c: int, max_c: int) -> str:
    body = text.strip()
    filler = (
        "\n\nОтдельный житейский совет перед первыми холодами: проверьте состояние термометров "
        "и уплотнителей на входной двери. В уфимских подъездах сквозняк через щели съедает до "
        "десяти процентов полезного домашнего тепла."
    )
    while len(body) < min_c:
        body = (body + filler).strip()
        if len(body) > max_c:
            break
    if len(body) > max_c:
        # truncate safely at sentence boundary or space
        body = body[: max_c - 1].rsplit(" ", 1)[0]
    return body.strip()


def render_post(news: dict, tenant: dict) -> str:
    angle = news.get("angle")
    if angle == "home_repair":
        raw = _home_repair_body(news)
    elif angle == "family_budget":
        raw = _family_budget_body(news)
    else:
        raw = _utility_bills_body(news)
    spec = tenant["post"]
    return _fit_length(raw, int(spec["min_chars"]), int(spec["max_chars"]))


def generate(
    vk_root: Path,
    today: date,
    seed: str,
    used_compositions: list[str],
    preferred_composition: str = "magazine-cover-ufa",
) -> dict[str, Any]:
    tenant = load_tenant(vk_root)
    banned = load_banned(vk_root)
    news_bank = _load_json(vk_root / "data" / "news-bank.json")
    compositions = _load_json(vk_root / "data" / "compositions.json")["compositions"]
    news = pick_news(news_bank["items"], today)
    composition = pick_composition(compositions, seed, used_compositions, preferred_id=preferred_composition)
    headline, description = pick_headline_and_description(news, seed, tenant)
    post = render_post(news, tenant)

    errors = validate_post(post, tenant, banned)
    errors.extend(validate_headline(headline, tenant, banned))
    errors.extend(validate_description(description, tenant, banned))
    if errors:
        raise RuntimeError("post validation failed: " + "; ".join(errors))

    return {
        "post": post,
        "headline": headline,
        "description": description,
        "news": news,
        "composition": composition,
        "char_count": len(post),
    }
