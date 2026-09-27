import re
import asyncio
import jdatetime
from calendar import month

from playwright.async_api import async_playwright


PERSIAN_DIGITS = str.maketrans(
    "۰۱۲۳۴۵۶۷۸۹",
    "0123456789"
)

ENGLISH_DIGITS = str.maketrans(
    "0123456789",
    "۰۱۲۳۴۵۶۷۸۹"
)

AIRLINE_PATTERN = (
    r"(پویا|ماهان|آوا|فلای کیش|ایران ایرتور|ایران ایر|هما|"
    r"آسمان|قشم ایر|کیش ایر|وارش|زاگرس|جی اسکای ایرلاین|مهر ایرلاین|تابان|ساها|"
    r"کاسپین|سپهران|معراج|چابهار|پارس ایر|آتا|"
    r"نفت ایر|اروان|یاز ایر)"
)

CABIN_PATTERN = r"(اکونومی|بیزینس|فرست کلاس)"

JALALI_MONTHS = [
    "فروردین", "اردیبهشت", "خرداد", "تیر",
    "مرداد", "شهریور", "مهر", "آبان",
    "آذر", "دی", "بهمن", "اسفند",
]


def fa_to_en(text: str) -> str:
    """Convert Persian digits to English digits."""
    return text.translate(PERSIAN_DIGITS)


def en_to_fa(text: str) -> str:
    """Convert English digits to Persian digits."""
    return text.translate(ENGLISH_DIGITS)


def extract_airlines_and_cabins(text: str) -> dict:
    airlines = re.findall(AIRLINE_PATTERN, text)
    cabins = re.findall(CABIN_PATTERN, text)

    return {
        "outbound_airline": airlines[0] if len(airlines) > 0 else None,
        "return_airline": airlines[1] if len(airlines) > 1 else None,
        "outbound_cabin_class": cabins[0] if len(cabins) > 0 else None,
        "return_cabin_class": cabins[1] if len(cabins) > 1 else None,
    }


def get_calendar_index(month_name: str) -> int:
    today = jdatetime.date.today()
    # 1..12
    current_month_number = today.month
    # Convert to 0-based index
    current_index = current_month_number - 1
    current_month_name = JALALI_MONTHS[current_index]
    next_month_name = JALALI_MONTHS[(current_index + 1) % 12]

    if month_name == current_month_name:
        return 0
    elif month_name == next_month_name:
        return 1
    else:
        raise ValueError(
            f"Only current ({current_month_name}) and next ({next_month_name}) months are supported"
        )


async def open_passenger_selector(page):
    passenger_button = page.get_by_role(
        "button",
        name="۱ مسافر",
        exact=True
    )

    if await passenger_button.count() == 0:
        raise RuntimeError("Passenger button not found")

    passenger_container = page.locator(
        "div.relative.w-full.flex-1.border-b.md\\:border-none"
    ).filter(
        has=page.get_by_text("تعداد مسافر", exact=True)
    )

    if await passenger_container.count() == 0:
        raise RuntimeError(
            "Passenger container not found"
        )

    passenger_button = passenger_container.get_by_role(
        "button"
    )

    await passenger_button.click()


async def select_route(page, origin, destination): 
    await page.get_by_role("button", name="مبدا").click()
    origin_input = page.get_by_placeholder("جستجوی مبدا")
    await origin_input.fill(origin)

    await page.wait_for_timeout(1000)

    suggestions = page.locator(
        "ul.scrollbar li.cursor-pointer"
    )

    if await suggestions.count() == 0:
        raise RuntimeError(
            f"No origin suggestions found for {origin}"
        )

    await suggestions.first.click()

    await page.wait_for_timeout(1000)

    await page.get_by_role("button", name="مقصد").click()
    destination_input = page.get_by_placeholder("جستجوی مقصد")
    await destination_input.fill(destination)

    await page.wait_for_timeout(1000)

    suggestions = page.locator(
        "ul.scrollbar li.cursor-pointer"
    )

    if await suggestions.count() == 0:
        raise RuntimeError(
            f"No destination suggestions found for {destination}"
        )

    await suggestions.first.click()


async def select_travel_dates(page, departure_day, return_day, departure_month, return_month):

    departure_day = en_to_fa(str(departure_day))
    return_day = en_to_fa(str(return_day))

    date_input = page.get_by_placeholder(
        "تاریخ رفت"
    )

    if await date_input.count() == 0:
        raise RuntimeError(
            "تاریخ رفت input not found"
        )

    await date_input.click()

    await page.wait_for_timeout(500)

    calendars = page.locator(
        "div.table-module-scss-module__lNwLWG__container"
    )

    if await calendars.count() < 1:
        raise RuntimeError(
            "Calendar not found"
        )

    month_id = get_calendar_index(month_name=departure_month)
    calendar = calendars.nth(month_id) 

    departure_day_ = calendar.get_by_text(
        departure_day,
        exact=True
    )

    if await departure_day_.count() == 0:
        raise RuntimeError(
            f"Departure date {departure_day} not found"
        )

    await departure_day_.first.click()

    await page.wait_for_timeout(500)

    month_id = get_calendar_index(month_name=return_month)
    calendar = calendars.nth(month_id) 

    return_day_ = calendar.get_by_text(
        return_day,
        exact=True
    )

    if await return_day_.count() == 0:
        raise RuntimeError(
            f"Return date {return_day} not found"
        )

    await return_day_.first.click()

    await page.wait_for_timeout(500)

    confirm_button = page.get_by_text(
        "تایید",
        exact=True
    )

    if await confirm_button.count() == 0:
        raise RuntimeError(
            "تایید button not found"
        )

    await confirm_button.first.click()

async def select_trip_type(page):
    trip_type_button = page.locator("button").filter(
        has_text="یک طرفه"
    )
    if await trip_type_button.count() == 0:
        raise RuntimeError(
            "یک طرفه button not found"
        )

    clicked = False
    for i in range(await trip_type_button.count()):
        button = trip_type_button.nth(i)
        if await button.is_visible():
            await button.click()
            clicked = True
            break

    if not clicked:
        raise RuntimeError(
            "No visible یک طرفه button found"
        )

    await page.wait_for_timeout(500)

    round_trip_option = page.get_by_text(
        "رفت و برگشت",
        exact=True
    )

    if await round_trip_option.count() == 0:
        raise RuntimeError(
            "رفت و برگشت option not found"
        )

    clicked = False
    for i in range(await round_trip_option.count()):
        option = round_trip_option.nth(i)
        if await option.is_visible():
            await option.click()
            clicked = True
            break

    if not clicked:
        raise RuntimeError(
            "No visible رفت و برگشت option found"
        )


def extract_times(text: str) -> dict:
    """
    Extract:
    - outbound departure/arrival
    - return departure/arrival
    """
    times = re.findall(r"[۰-۹]{1,2}:[۰-۹]{2}", text)
    times = [fa_to_en(t) for t in times]

    return {
        "outbound_departure_time": times[0] if len(times) > 0 else None,
        "outbound_arrival_time": times[1] if len(times) > 1 else None,
        "return_departure_time": times[2] if len(times) > 2 else None,
        "return_arrival_time": times[3] if len(times) > 3 else None,
    }

def extract_price(text: str) -> int | None:
    match = re.search(
        r"قیمت برای هر بزرگسال\s*(?:رفت و برگشت\s*)?([\d۰-۹,]+)\s*تومان",
        text,
        flags=re.S,
    )

    if not match:
        return None

    return int(fa_to_en(match.group(1)).replace(",", ""))


async def inspect_results(page) -> dict:
    cards = page.locator('[data-testid="solution-card"]')
    try:
        await cards.first.wait_for(
            state="visible",
            timeout=30_000,
        )
    except TimeoutError:
        return {"flights": []}
    
    count = await cards.count()

    if count == 0:
        return {"flights": []}

    flights = []

    for i in range(count):
        card = cards.nth(i)
        card_text = await card.inner_text()

        times = extract_times(card_text)
        price = extract_price(card_text)
        info = extract_airlines_and_cabins(card_text)

        flights.append({
            "index": i + 1,
            "outbound": {
                "departure_time": times["outbound_departure_time"],
                "arrival_time": times["outbound_arrival_time"],
                "airline": info["outbound_airline"],
                "cabin_class": info["outbound_cabin_class"],
            },
            "return": {
                "departure_time": times["return_departure_time"],
                "arrival_time": times["return_arrival_time"],
                "airline": info["return_airline"],
                "cabin_class": info["return_cabin_class"],
            },
            "price_per_adult": price,
            "currency": "Tooman",
        })

    return {"flights": flights}

async def click_search(page):
    """
    Click the final flight search button.
    """
    search_button = page.get_by_role(
        "button",
        name="جستجو",
        exact=True
    )

    if await search_button.count() == 0:
        raise RuntimeError(
            "جستجو button not found"
        )

    await search_button.first.click()
    await page.wait_for_load_state("domcontentloaded")

    await page.wait_for_timeout(3000)

async def select_passengers(
    page,
    adults: int = 1,
    children: int = 0,
    infants: int = 0,
):
    """
    Select passenger counts.

    Passenger categories:
        0 -> بزرگسال
        1 -> کودک
        2 -> نوزاد

    SnappTrip initial state:
        بزرگسال = 1
        کودک     = 0
        نوزاد    = 0
    """
    if adults < 1:
        raise ValueError(
            "At least one adult is required"
        )

    if children < 0:
        raise ValueError(
            "children cannot be negative"
        )

    if infants < 0:
        raise ValueError(
            "infants cannot be negative"
        )

    passenger_container = page.locator(
        "div.relative.w-full.flex-1.border-b.md\\:border-none"
    ).filter(
        has=page.get_by_text(
            "تعداد مسافر",
            exact=True
        )
    )

    if await passenger_container.count() == 0:
        raise RuntimeError(
            "Passenger container not found"
        )

    passenger_button = passenger_container.first.locator(
        "button"
    ).first

    if await passenger_button.count() == 0:
        raise RuntimeError(
            "Passenger button not found"
        )

    await passenger_button.click(
        force=True,
        timeout=5000
    )

    await page.wait_for_timeout(300)

    plus_buttons = page.get_by_role(
        "button",
        name="+",
        exact=True
    )

    minus_buttons = page.get_by_role(
        "button",
        name="-",
        exact=True
    )

    if await plus_buttons.count() != 3:
        raise RuntimeError(
            "Expected exactly 3 '+' buttons"
        )

    if await minus_buttons.count() != 3:
        raise RuntimeError(
            "Expected exactly 3 '-' buttons"
        )

    current = [
        1,  # بزرگسال
        0,  # کودک
        0,  # نوزاد
    ]

    target = [
        adults,
        children,
        infants,
    ]

    categories = [
        "بزرگسال",
        "کودک",
        "نوزاد",
    ]

    for index in range(3):
        current_count = current[index]
        target_count = target[index]

        if target_count > current_count:
            clicks = target_count - current_count
            for _ in range(clicks):
                await plus_buttons.nth(index).click()
                await page.wait_for_timeout(100)

        elif target_count < current_count:
            clicks = current_count - target_count
            for _ in range(clicks):
                await minus_buttons.nth(index).click()
                await page.wait_for_timeout(100)


    confirm_button = page.get_by_role(
        "button",
        name="تایید",
        exact=True
    )

    if await confirm_button.count() == 0:
        raise RuntimeError(
            "تایید button not found"
        )

    await confirm_button.first.click()
    await page.wait_for_timeout(500)


async def execute_flight_search(
        origin, 
        destination, 
        departure_day, 
        return_day, 
        departure_month, 
        return_month, 
        adults, 
        children, 
        infants):
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            executable_path="/usr/bin/google-chrome",
            headless=True,
        )

        page = await browser.new_page()

        await page.goto(
            "https://www.snapptrip.com/flights",
            wait_until="domcontentloaded",
        )

        print("STATUS:", await page.title())
        print("URL:", page.url)

        await select_route(page, origin, destination)

        await page.wait_for_timeout(1000)

        await select_trip_type(page)

        await page.wait_for_timeout(500)

        await select_travel_dates(
            page, 
            departure_day, 
            return_day, 
            departure_month, 
            return_month)

        await page.wait_for_timeout(1000)

        await open_passenger_selector(page)

        await page.wait_for_timeout(500)

        await select_passengers(
            page,
            adults,
            children,
            infants,
        )

        await click_search(page)

        await page.wait_for_load_state("domcontentloaded")
        await page.wait_for_timeout(500)

        results = await inspect_results(page)

        await browser.close()

        return results


if __name__ == "__main__":
    asyncio.run(
        execute_flight_search(
            origin="تهران", 
            destination="مشهد", 
            departure_day=25, 
            return_day=26, 
            departure_month="مهر", 
            return_month="مهر", 
            adults=2, 
            children=1, 
            infants=0
        )
    )