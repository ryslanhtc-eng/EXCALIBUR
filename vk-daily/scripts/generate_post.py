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


def pick_news(items: list[dict], today: date, news_id: str = "") -> dict:
    if news_id:
        for item in items:
            if str(item.get("id")) == news_id:
                return item
        raise RuntimeError(f"news-bank has no item with id {news_id!r}")
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
    if angle == "rent_spike":
        return [
            "Однушка в Уфе уже двадцать пять",
            "Аренда подскочила за август",
            "Спрос на съём вырос на треть",
            "Долгосрок снова бьёт по кошельку",
        ]
    return ["Уфа считает квартирный шаг", "Честный разбор без метро"]


def pick_headline(news: dict, seed: str, tenant: dict) -> str:
    options = _headlines_for(news)
    digest = hashlib.sha256((seed + "|headline").encode("utf-8")).hexdigest()
    ordered = [options[int(digest, 16) % len(options)]] + options
    for candidate in ordered:
        if not validate_headline(candidate, tenant):
            return candidate
    raise RuntimeError("no valid cover headline")


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

Второе. В Уфе нет метро. И в Сипайлово его тоже нет. Если в тексте "5 минут до метро" – это копипаст из другого города. Такое объявление можно закрывать без сожаления. 😅 У нас маршрут – автобус, трамвай, электричка, машина и пробки на выезде. Это честнее несуществующей станции.

Третье. Пока в республике большой навес непроданных квартир, застройщикам незачем прыгать на 3-4% в месяц. Спокойный шаг 0,3-0,5% реалистичнее паники "завтра убежит". Паника обычно дороже, чем вечер с калькулятором.

Если жильё нужно под семейную программу – пересчитайте платёж до осени. Условия уже сужали, и октябрь не про погоду, а про то, что часть семей просто не пройдёт в ту же корзину.

Я Руслан Мухтаров, Самолет Плюс, Уфа. Не продаю воздух с выдуманным метро. Могу пройтись по вашему объекту: платёж, риски, торг, документы.

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

Ещё раз про транспорт, потому что шаблоны объявлений живучи. Метро в Уфе нет. "У метро Сипайлово" – враньё или копипаст. Есть автобус, электричка, машина, пробки. Если вам продают станцию – продают чужой город.

Я не тороплю "закрыть сегодня". Я предлагаю закрыть самообман: сравнить три лота на бумаге, прикинуть платёж, посмотреть дом днём, не в золотом закате с дрона.

Руслан Мухтаров, Самолет Плюс. Напишите в сообщения сообщества, если нужен разбор вашего варианта без воды и без выдуманного метро."""


def _rent_spike_body(news: dict) -> str:
    numbers = news.get("numbers") or {}
    r1 = numbers.get("rent_1k_rub", 25400)
    r1_pct = numbers.get("rent_1k_mom_pct", 7.8)
    r2 = numbers.get("rent_2k_rub", 32300)
    r2_pct = numbers.get("rent_2k_mom_pct", 5.9)
    demand = numbers.get("demand_mom_pct", 27)
    r1_txt = f"{r1 / 1000:.1f}".replace(".", ",")
    r2_txt = f"{r2 / 1000:.1f}".replace(".", ",")
    r1_pct_txt = str(r1_pct).replace(".", ",")
    r2_pct_txt = str(r2_pct).replace(".", ",")
    demand_txt = str(demand).replace(".", ",")
    return f"""Аренда в Уфе снова напомнила, что «временно сниму пару месяцев» часто превращается в год. Август по цифрам «Мир квартир»: однокомнатная +{r1_pct_txt}% и около {r1_txt} тыс. рублей в месяц, двухкомнатная +{r2_pct_txt}% и примерно {r2_txt} тыс. Параллельно Авито фиксирует спрос на долгосрок +{demand_txt}% за месяц. Это не абстрактная «инфляция», это конкретный платёж из зарплаты.

Если вы ищете жильё в Сипайлово, Дёме, Инорсе или на вторичке в центре, картина одна: объявлений мало, хозяева реже устраивают конкурс из десяти анкет, а арендаторы чаще остаются на месте и не сдают «на лето».

Что я вижу на показах и в переписке.

Первое. Цифра в заголовке объявления и цена на встрече расходятся. «25 тысяч, но без мебели, но счётчики отдельно, но залог двойной» уже другая история. Считайте полный чек: депозит, коммуналка, интернет, мелкий ремонт, если что-то сломалось в первую неделю.

Второе. Спрос +{demand_txt}% не значит, что любую однушку заберут за час. Заберут лот, где честные фото, нормальный двор и адекватный договор. Копипаст «идеальная квартира для семьи» без кухни на фото вызывает у меня только вопросы. 😅

Третье. Если вы сдаёте, не гонитесь за максимумом в объявлении и потом сидите пустым месяц. Лучше чуть ниже рынка и живой арендатор с рекомендацией, чем красивая цифра и простой. Если снимаете, не подписывайте «на всякий случай» допсоглашения, которые не читали.

Четвёртое. Покупка vs аренда сейчас не про лозунги. Сравните платёж по ипотеке на ваш реальный лот и аренду на похожий. Иногда аренда выигрывает год-два, иногда наоборот. Без таблицы это всегда эмоции.

Я Руслан Мухтаров, «Самолет Плюс», Уфа. Офис: ул. Жукова, 39/1, офис 303, Сипайлово. Помогаю и снимающим, и сдающим: договор, приёмка, торг, проверка хозяина, а не только «найти объявление».

Напишите в сообщения сообщества, если нужен разбор вашей ситуации по цифрам, без воды и без красивых обещаний."""


def _mortgage_body(_news: dict) -> str:
    return """Семейную ипотеку уже резали, а к октябрю снова ждут ужесточение шкалы. Если вы в программу проходите – это не призыв "хватай любую двушку". Это призыв сесть и посчитать платёж на тех условиях, которые есть сейчас, а не на тех, которые обещает картинка в сторис.

Экспертный разговор в Уфе в начале сентября был прямой: лучших времён можно не дождаться. Согласен с осторожной частью. Не согласен с паникой. Платёж, который не встаёт в зарплату, не станет добрее от того, что "ставка ещё подрастёт".

Что делать руками. Собрать семью, сертификаты, доход. Попросить банк или брокера нарисовать график. Параллельно смотреть 2-3 живых лота в Сипайлово, Дёме, на вторичке – не 15 вкладок "для вдохновения". В Уфе нет метро, зато есть понятный вопрос: сколько ехать на работу и сколько отдавать банку.

Если в объявлении семейная ставка и копипаст про метро – закройте. Ставку без договора я в пост не пишу: банки меняют условия быстрее, чем лента. А метро у нас всё так же нет.

Я Руслан Мухтаров, Самолет Плюс, Уфа. Могу помочь собрать документы и не купить дом, который красивый только в карусели.

Напишите в сообщения сообщества – разложим цифры спокойно."""


def _fit_length(text: str, min_c: int, max_c: int) -> str:
    body = text.strip()
    filler = (
        "\n\nЕщё одна бытовая проверка перед показом: посмотрите дом в обычный будний час, "
        "не в воскресенье. Двор, парковка, шум с дороги, магазин пешком. В Уфе это решает "
        "больше, чем красивое слово в шапке объявления."
    )
    while len(body) < min_c:
        body = (body + filler).strip()
        if len(body) > max_c:
            break
    if len(body) > max_c:
        body = body[: max_c - 1].rsplit(" ", 1)[0]
    return body.strip()


def cover_dek_for(news: dict) -> str:
    angle = news.get("angle") or ""
    if angle == "rent_spike":
        numbers = news.get("numbers") or {}
        r1 = numbers.get("rent_1k_rub", 25400)
        demand = numbers.get("demand_mom_pct", 27)
        r1_txt = f"{r1 / 1000:.1f}".replace(".", ",")
        demand_txt = str(demand).replace(".", ",")
        return f"Август: однушки ~{r1_txt} тыс, спрос +{demand_txt}%"
    return "Уфа, честные цифры без паники"


def render_post(news: dict, tenant: dict) -> str:
    angle = news.get("angle")
    if angle == "avg_ticket":
        raw = _avg_ticket_body(news)
    elif angle == "mortgage_window":
        raw = _mortgage_body(news)
    elif angle == "rent_spike":
        raw = _rent_spike_body(news)
    else:
        raw = _price_pulse_body(news)
    spec = tenant["post"]
    return _fit_length(raw, int(spec["min_chars"]), int(spec["max_chars"]))


def generate(
    vk_root: Path,
    today: date,
    seed: str,
    used_compositions: list[str],
    news_id: str = "",
) -> dict[str, Any]:
    tenant = load_tenant(vk_root)
    banned = load_banned(vk_root)
    news_bank = _load_json(vk_root / "data" / "news-bank.json")
    compositions = _load_json(vk_root / "data" / "compositions.json")["compositions"]
    news = pick_news(news_bank["items"], today, news_id=news_id)
    composition = pick_composition(compositions, seed, used_compositions)
    headline = pick_headline(news, seed, tenant)
    post = render_post(news, tenant)

    errors = validate_post(post, tenant, banned)
    errors.extend(validate_headline(headline, tenant))
    if errors:
        raise RuntimeError("post validation failed: " + "; ".join(errors))

    return {
        "post": post,
        "headline": headline,
        "cover_dek": cover_dek_for(news),
        "news": news,
        "composition": composition,
        "char_count": len(post),
    }
