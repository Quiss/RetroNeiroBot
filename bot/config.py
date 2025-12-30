"""Модуль для загрузки конфигурации бота"""
import os
from dataclasses import dataclass
from pathlib import Path
from typing import List

import yaml
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()


@dataclass
class GenerationConfig:
    """Настройки генераций"""
    initial_count: int
    referral_bonus: int


@dataclass
class PricingTier:
    """Тариф покупки генераций"""
    generations: int
    price: int
    currency: str
    subtext: str


@dataclass
class OpenRouterConfig:
    """Настройки OpenRouter"""
    model: str
    generation_prompt: str


@dataclass
class BotConfig:
    """Настройки бота"""
    image_caption: str
    bot_username: str
    support_url: str


@dataclass
class DocumentsConfig:
    """Ссылки на документы"""
    privacy_policy: str
    terms_of_service: str


@dataclass
class LoggingConfig:
    """Настройки логирования"""
    level: str
    format: str
    rotation: str
    retention: str


@dataclass
class PaymentConfig:
    """Настройки платежей"""
    driver: str


@dataclass
class RobokassaConfig:
    """Настройки Robokassa"""
    merchant_login: str
    password1: str
    password2: str
    test_mode: bool


@dataclass
class OtherProcessingButton:
    """Кнопка в разделе 'Другие обработки'"""
    text: str
    url: str


@dataclass
class Config:
    """Главная конфигурация приложения"""
    # Переменные окружения
    bot_token: str
    database_url: str
    openrouter_api_key: str

    # Конфигурация из YAML
    generations: GenerationConfig
    pricing: List[PricingTier]
    openrouter: OpenRouterConfig
    bot: BotConfig
    documents: DocumentsConfig
    logging: LoggingConfig
    payment: PaymentConfig
    robokassa: RobokassaConfig
    other_processing_buttons: List[OtherProcessingButton]


def load_config() -> Config:
    """Загрузка конфигурации из файлов и переменных окружения"""

    # Загрузка переменных окружения
    bot_token = os.getenv("BOT_TOKEN")
    database_url = os.getenv("DATABASE_URL")
    openrouter_api_key = os.getenv("OPENROUTER_API_KEY")

    if not bot_token:
        raise ValueError("BOT_TOKEN не установлен в переменных окружения")
    if not database_url:
        raise ValueError("DATABASE_URL не установлен в переменных окружения")
    if not openrouter_api_key:
        raise ValueError("OPENROUTER_API_KEY не установлен в переменных окружения")

    # Загрузка YAML конфигурации
    config_path = Path(__file__).parent.parent / "config" / "config.yaml"

    if not config_path.exists():
        raise FileNotFoundError(f"Файл конфигурации не найден: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        yaml_config = yaml.safe_load(f)

    # Парсинг конфигурации
    generations = GenerationConfig(
        initial_count=yaml_config["generations"]["initial_count"],
        referral_bonus=yaml_config["generations"]["referral_bonus"]
    )

    pricing = [
        PricingTier(
            generations=tier["generations"],
            price=tier["price"],
            currency=tier["currency"],
            subtext=tier["subtext"]
        )
        for tier in yaml_config["pricing"]
    ]

    openrouter = OpenRouterConfig(
        model=yaml_config["openrouter"]["model"],
        generation_prompt=yaml_config["openrouter"]["generation_prompt"]
    )

    bot = BotConfig(
        image_caption=yaml_config["bot"]["image_caption"],
        bot_username=yaml_config["bot"]["bot_username"],
        support_url=yaml_config["bot"]["support_url"]
    )

    documents = DocumentsConfig(
        privacy_policy=yaml_config["documents"]["privacy_policy"],
        terms_of_service=yaml_config["documents"]["terms_of_service"]
    )

    logging = LoggingConfig(
        level=yaml_config["logging"]["level"],
        format=yaml_config["logging"]["format"],
        rotation=yaml_config["logging"]["rotation"],
        retention=yaml_config["logging"]["retention"]
    )

    payment = PaymentConfig(
        driver=yaml_config["payment"]["driver"]
    )

    # Загрузка настроек Robokassa из переменных окружения
    robokassa_merchant_login = os.getenv("ROBOKASSA_MERCHANT_LOGIN", "")
    robokassa_password1 = os.getenv("ROBOKASSA_PASSWORD1", "")
    robokassa_password2 = os.getenv("ROBOKASSA_PASSWORD2", "")
    robokassa_test_mode = os.getenv("ROBOKASSA_TEST_MODE", "true").lower() == "true"

    robokassa = RobokassaConfig(
        merchant_login=robokassa_merchant_login,
        password1=robokassa_password1,
        password2=robokassa_password2,
        test_mode=robokassa_test_mode
    )

    # Парсинг кнопок "Другие обработки"
    other_processing_buttons = [
        OtherProcessingButton(
            text=button["text"],
            url=button["url"]
        )
        for button in yaml_config.get("other_processing_buttons", [])
    ]

    return Config(
        bot_token=bot_token,
        database_url=database_url,
        openrouter_api_key=openrouter_api_key,
        generations=generations,
        pricing=pricing,
        openrouter=openrouter,
        bot=bot,
        documents=documents,
        logging=logging,
        payment=payment,
        robokassa=robokassa,
        other_processing_buttons=other_processing_buttons
    )


# Глобальный экземпляр конфигурации
config = load_config()
