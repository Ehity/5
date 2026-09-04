"""База прямых ссылок на управление/отмену подписок для известных сервисов."""

CANCEL_LINKS = {
    "Яндекс Плюс": "https://plus.yandex.ru/my",
    "Netflix": "https://www.netflix.com/cancelplan",
    "Иви": "https://www.ivi.ru/profile/subscription",
    "Telegram Premium": "https://t.me/PremiumBot",
    "Okko": "https://okko.tv/profile/subscriptions",
    "VK Музыка": "https://id.vk.com/pay/subscriptions",
    "VK Combo": "https://id.vk.com/pay/subscriptions",
    "KION": "https://kion.ru/profile/subscriptions",
    "Кинопоиск": "https://hd.kinopoisk.ru/profile",
    "Spotify": "https://www.spotify.com/account/overview/",
    "iCloud+": "https://appleid.apple.com/",
    "YouTube Premium": "https://www.youtube.com/paid_memberships",
    "СберПрайм": "https://sberprime.ru/profile",
    "WORLD CLASS": "https://www.worldclass.ru/",
}


def get_cancel_url(service_name: str) -> str:
    """Возвращает прямую ссылку на отмену подписки или фоллбек на поиск."""
    if service_name in CANCEL_LINKS:
        return CANCEL_LINKS[service_name]
    query = "how to cancel subscription " + service_name.strip()
    return "https://yandex.ru/search/?text=" + query.replace(" ", "+")


def enrich_subscriptions(subs: list) -> list:
    """Добавляет поле cancel_url каждой подписке."""
    for s in subs:
        s["cancel_url"] = get_cancel_url(s.get("name", ""))
    return subs
