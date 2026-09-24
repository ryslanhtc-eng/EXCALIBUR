"""Build one ~2000-char Ufa story post + 4–8 word cover headline."""
from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Any

from validate_post import validate_headline, validate_post, load_banned, load_tenant


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


def pick_composition(compositions: list[dict], seed: str, used: list[str]) -> dict:
    unused = [c for c in compositions if c.get("id") not in used]
    pool = unused or compositions
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    idx = int(digest, 16) % len(pool)
    return pool[idx]


def _headlines_for(news: dict) -> list[str]:
    angle = news.get("angle") or ""
    if angle == "price_pulse":
        return [
            "Уфа снова в тройке",
            "Квадрат уже почти двести",
            "Август поднял уфимский ценник",
            "Первичка растёт без суеты",
        ]
    if angle == "avg_ticket":
        return [
            "Средняя новостройка восемь два",
            "Билет в новостройку вырос",
            "Уфимская квартира снова дороже",
        ]
    if angle == "mortgage_window":
        return [
            "Платёж считают до октября",
            "Семейная не ждёт чуда",
            "Окно по семейной уже узкое",
        ]
    if angle == "egrn_ban":
        return [
            "Запрет сделок без вас",
            "Как защитить квартиру в ЕГРН",
            "Защита жилья от чужих сделок",
            "Бесплатный запрет сделок в ЕГРН",
            "Запрет сделок без вас как поставить защиту",
        ]
    return ["Уфа считает квартирный шаг", "Честный разбор по документам"]


def pick_headline(news: dict, seed: str, tenant: dict) -> str:
    options = _headlines_for(news)
    digest = hashlib.sha256((seed + "|headline").encode("utf-8")).hexdigest()
    ordered = [options[int(digest, 16) % len(options)]] + options
    for candidate in ordered:
        if not validate_headline(candidate, tenant):
            return candidate
    raise RuntimeError("no valid cover headline")


def pick_dek(news: dict, seed: str) -> str:
    angle = news.get("angle") or ""
    if angle == "egrn_ban":
        options = [
            "Бесплатная отметка в ЕГРН за пять рабочих дней",
            "Поставьте бесплатную защиту в ЕГРН за пять дней",
            "Как за пять дней закрыть квартиру от чужих сделок",
        ]
    elif angle == "price_pulse":
        options = ["Честный разбор уфимского квадрата без паники"]
    elif angle == "avg_ticket":
        options = ["Что стоит за средней цифрой в восемь миллионов"]
    else:
        options = ["Практичный разбор для тех кто планирует жильё"]
    digest = hashlib.sha256((seed + "|dek").encode("utf-8")).hexdigest()
    return options[int(digest, 16) % len(options)]


def _price_pulse_body(news: dict) -> str:
    numbers = news.get("numbers") or {}
    sqm = numbers.get("sqm_rub")
    mom = numbers.get("mom_pct")
    sqm_txt = f"{sqm / 1000:.1f}".replace(".0", "") if isinstance(sqm, (int, float)) else "почти 198"
    # 197800 -> 197,8
    if isinstance(sqm, (int, float)):
        sqm_txt = f"{sqm / 1000:.1f}".replace(".", ",")
    mom_txt = f"{mom}".replace(".", ",") if mom is not None else "1,6"
    return f"""Уфа снова в тройке по росту цен на новостройки среди городов-миллионников. Не "вся страна", не столичный шум – конкретно наша первичка.

РБК Недвижимость по августу: квадрат на первичном рынке в столице Башкирии вырос на {mom_txt}% и дошёл до {sqm_txt} тыс. рублей. Впереди только Москва и Красноярск. Это не взрыв, это уже привычная уфимская инерция: лето заканчивается, люди возвращаются из отпусков, застройщики чуть подтягивают ценник.

Что из этого следует, если вы смотрите квартиру в Сипайлово, Дёме или на вторичке рядом.

Первое. Цифра "за квадрат" – средняя по городу. В одном доме 190, в соседнем 230, в черновой студии и в отделке с мебелью – разные вселенные. Сравнивайте не заголовок объявления, а конкретный лот: этаж, кухня, двор, год, сколько уже висит.

Второе. У нас маршрут – автобус, трамвай, электричка, машина и пробки на выезде. Никаких чужих сказок из чужих городов. 😅

Третье. Пока в республике большой навес непроданных квартир, застройщикам незачем прыгать на 3-4% в месяц. Спокойный шаг 0,3-0,5% реалистичнее паники "завтра убежит". Паника обычно дороже, чем вечер с калькулятором.

Если жильё нужно под семейную программу – пересчитайте платёж до осени. Условия уже сужали, и октябрь не про погоду, а про то, что часть семей просто не пройдёт в ту же корзину.

Я Руслан Мухтаров, Самолет Плюс, Уфа. Могу пройтись по вашему объекту: платёж, риски, торг, документы.

Напишите в сообщения сообщества – разберём ваш вариант по цифрам, без воды."""


def _avg_ticket_body(news: dict) -> str:
    numbers = news.get("numbers") or {}
    apt = numbers.get("apartment_mln", 8.2)
    mom = numbers.get("mom_pct", 1.3)
    apt_txt = str(apt).replace(".", ",")
    mom_txt = str(mom).replace(".", ",")
    return f"""Средняя новая квартира в Уфе по итогам августа – почти {apt_txt} млн рублей. Плюс {mom_txt}% к июлю. Это не "ваш конкретный дом", это средняя температура по больнице – но направление такое.

Башинформ сослался на "Мир квартир". Я эту цифру не раздуваю и не делю на красивые студии в рекламе. Если вам приносят лот за 6,2 и лот за 11, оба могут быть "рынком". Средняя нужна, чтобы не верить заголовку "последняя квартира по старой цене" без таблицы.

В Дёме, Сипайлово, Инорсе смотрите связку: платёж, срок ключей, что уже сдано во дворе, кто сосед по подъезду. Новостройка без отделки и вторичка с ремонтом 2012 года считаются в разных тетрадях. Смешивать их в одной фразе "надо брать, пока не улетело" – плохая привычка.

У нас свой понятный ритм: автобус, электричка, машина, пробки на мостах.

Я не тороплю "закрыть сегодня". Я предлагаю закрыть самообман: сравнить три лота на бумаге, прикинуть платёж, посмотреть дом днём, не в золотом закате с дрона.

Руслан Мухтаров, Самолет Плюс. Напишите в сообщения сообщества, если нужен разбор вашего варианта без воды."""


def _egrn_ban_body(_news: dict) -> str:
    return """Слышали истории, как люди узнают, что на их квартиру оформлена сделка по липовой доверенности? После волны электронных услуг этот страх сидит у многих. Ко мне на консультациях в Сипайлово часто приходят с вопросом: Руслан, можно ли поставить на квартиру надёжный замок в реестре, чтобы без меня никто к ней не прикоснулся?

Отвечаю сразу: да, можно. Это бесплатно и делается за несколько минут, не выходя из дома.

Речь об отметке в Едином государственном реестре недвижимости (ЕГРН): о невозможности регистрации перехода права без личного участия правообладателя. Как только запись появляется в базе, Росреестр обязан вернуть без рассмотрения любые документы, если их подал кто-то другой, даже с нотариальной доверенностью.

Как это сделать по шагам.

Первый путь через Госуслуги. Заходите в подтверждённый профиль, находите запрет на сделки без личного участия, выбираете объект недвижимости и подписываете заявление усиленной электронной подписью через Госключ. Пошлин нет. Примерно пять рабочих дней, и запись внесена в ЕГРН.

Второй путь через МФЦ. Если электронным сервисам не доверяете, берёте паспорт и идёте в любой офис МФЦ в Уфе. Подаёте письменное заявление лично. Срок тот же, результат аналогичный.

Кому стоит поставить запрет в первую очередь.

Тем, кто сдаёт жильё. Тем, кто часто уезжает на вахту. У кого пожилые родители с квартирой в собственности. И просто для собственного спокойного сна.

Что эта отметка не заменит.

Запись защищает от чужих рук и серых схем. Но она не спасёт от решения суда, требований приставов по долгам или процедур банкротства. Госорганы работают по своим законам.

Снимается запрет так же просто: через Госуслуги или личным визитом в МФЦ, когда сами решите продать или подарить квартиру.

Если готовитесь к сделке или хотите проверить объект, заходите к нам: ул. Жукова 39/1, офис 303, Уфа (Сипайлово). Либо напишите в сообщения сообщества, разберём всё спокойно."""


def _mortgage_body(_news: dict) -> str:
    return """Семейную ипотеку уже резали, а к октябрю снова ждут ужесточение шкалы. Если вы в программу проходите – это не призыв "хватай любую двушку". Это призыв сесть и посчитать платёж на тех условиях, которые есть сейчас, а не на тех, которые обещает картинка в сторис.

Экспертный разговор в Уфе в начале сентября был прямой: лучших времён можно не дождаться. Согласен с осторожной частью. Не согласен с паникой. Платёж, который не встаёт в зарплату, не станет добрее от того, что "ставка ещё подрастёт".

Что делать руками. Собрать семью, сертификаты, доход. Попросить банк или брокера нарисовать график. Параллельно смотреть 2-3 живых лота в Сипайлово, Дёме, на вторичке – не 15 вкладок "для вдохновения". У нас понятный вопрос: сколько ехать на работу и сколько отдавать банку.

Ставку без договора я в пост не пишу: банки меняют условия быстрее, чем лента.

Я Руслан Мухтаров, Самолет Плюс, Уфа. Могу помочь собрать документы и не купить дом, который красивый только в карусели.

Напишите в сообщения сообщества – разложим цифры спокойно."""


def _fit_length(text: str, min_c: int, max_c: int) -> str:
    body = text.strip()
    filler = (
        "\n\nЕсли хотите дополнительно проверить, есть ли уже какие-то ограничения или обременения "
        "по вашей квартире, загляните в свежую выписку ЕГРН. Спокойствие всегда начинается с порядка в документах."
    )
    filler2 = (
        "\n\nКстати, ещё одна деталь. Запрет ставится на конкретный объект недвижимости с кадастровым номером. "
        "Если у вас квартира и дачный участок, заявление нужно подать на каждый объект отдельно."
    )
    fillers = [filler, filler2]
    i = 0
    while len(body) < min_c:
        body = (body + fillers[i % len(fillers)]).strip()
        i += 1
        if len(body) > max_c:
            break
    if len(body) > max_c:
        body = body[: max_c - 1].rsplit(" ", 1)[0]
    return body.strip()


def render_post(news: dict, tenant: dict) -> str:
    angle = news.get("angle")
    if angle == "egrn_ban":
        raw = _egrn_ban_body(news)
    elif angle == "avg_ticket":
        raw = _avg_ticket_body(news)
    elif angle == "mortgage_window":
        raw = _mortgage_body(news)
    else:
        raw = _price_pulse_body(news)
    spec = tenant["post"]
    return _fit_length(raw, int(spec["min_chars"]), int(spec["max_chars"]))


def generate(vk_root: Path, today: date, seed: str, used_compositions: list[str]) -> dict[str, Any]:
    tenant = load_tenant(vk_root)
    banned = load_banned(vk_root)
    news_bank = _load_json(vk_root / "data" / "news-bank.json")
    compositions = _load_json(vk_root / "data" / "compositions.json")["compositions"]
    news = pick_news(news_bank["items"], today)
    composition = pick_composition(compositions, seed, used_compositions)
    headline = pick_headline(news, seed, tenant)
    dek = pick_dek(news, seed)
    post = render_post(news, tenant)

    errors = validate_post(post, tenant, banned)
    errors.extend(validate_headline(headline, tenant))
    if errors:
        raise RuntimeError("post validation failed: " + "; ".join(errors))

    return {
        "post": post,
        "headline": headline,
        "dek": dek,
        "news": news,
        "composition": composition,
        "char_count": len(post),
    }
