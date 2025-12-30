"""Модуль для настройки логирования"""
import sys
from pathlib import Path

from loguru import logger

# Удаляем стандартный обработчик
logger.remove()

# Создаем директорию для логов
logs_dir = Path(__file__).parent.parent / "logs"
logs_dir.mkdir(exist_ok=True)

# Настройка форматирования
log_format = (
    "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
    "<level>{message}</level>"
)

# Добавляем вывод в консоль
logger.add(
    sys.stdout,
    format=log_format,
    level="INFO",
    colorize=True,
)

# Добавляем вывод в файл
logger.add(
    logs_dir / "bot.log",
    format=log_format,
    level="DEBUG",
    rotation="10 MB",  # Ротация при достижении 10 МБ
    retention="1 week",  # Хранение логов за последнюю неделю
    compression="zip",  # Сжатие старых логов
    encoding="utf-8",
)

# Добавляем отдельный файл для ошибок
logger.add(
    logs_dir / "errors.log",
    format=log_format,
    level="ERROR",
    rotation="10 MB",
    retention="1 month",
    compression="zip",
    encoding="utf-8",
)

logger.info("Логирование настроено")
