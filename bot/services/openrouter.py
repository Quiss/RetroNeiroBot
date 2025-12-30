"""Сервис для работы с OpenRouter API"""
import asyncio
import base64
from io import BytesIO
from typing import Optional

import httpx
from aiogram.types import PhotoSize, BufferedInputFile

from bot.config import config
from bot.logger import logger


class OpenRouterService:
    """Класс для работы с OpenRouter API"""

    def __init__(self):
        self.api_url = "https://openrouter.ai/api/v1/chat/completions"
        self.api_key = config.openrouter_api_key
        self.model = config.openrouter.model
        self.prompt = config.openrouter.generation_prompt

    async def download_photo(self, bot, photo: PhotoSize) -> bytes:
        """
        Скачать фотографию от пользователя

        Args:
            bot: Экземпляр бота
            photo: Объект фотографии

        Returns:
            bytes: Содержимое фотографии
        """
        try:
            file = await bot.get_file(photo.file_id)
            downloaded_file = await bot.download_file(file.file_path)

            # Читаем содержимое
            if isinstance(downloaded_file, BytesIO):
                photo_bytes = downloaded_file.read()
            else:
                photo_bytes = downloaded_file

            logger.debug(f"Фото скачано: {len(photo_bytes)} байт")
            return photo_bytes

        except Exception as e:
            logger.error(f"Ошибка при скачивании фото: {e}")
            raise

    async def generate_image(self, image_bytes: bytes, max_retries: int = 3) -> Optional[bytes]:
        """
        Сгенерировать новое изображение на основе исходного с механизмом retry

        Args:
            image_bytes: Исходное изображение в байтах
            max_retries: Максимальное количество попыток (по умолчанию 3)

        Returns:
            bytes: Сгенерированное изображение или None при ошибке
        """
        # Кодируем изображение в base64 один раз
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')
        image_url = f"data:image/jpeg;base64,{image_base64}"

        # Подготовка запроса
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": self.prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": image_url
                            }
                        }
                    ]
                }
            ],
            "modalities": ["image", "text"]
        }

        # Попытки генерации с retry
        for attempt in range(1, max_retries + 1):
            try:
                logger.info(f"Попытка {attempt}/{max_retries}: Отправка запроса к OpenRouter, модель: {self.model}")

                # Отправка запроса к OpenRouter
                async with httpx.AsyncClient(timeout=300.0) as client:
                    response = await client.post(
                        self.api_url,
                        headers=headers,
                        json=payload
                    )

                    if response.status_code != 200:
                        logger.warning(
                            f"Попытка {attempt}/{max_retries}: Ошибка OpenRouter API: "
                            f"{response.status_code} - {response.text}"
                        )
                        # Если это не последняя попытка, ждем и пробуем снова
                        if attempt < max_retries:
                            await asyncio.sleep(2 * attempt)  # Увеличивающаяся задержка
                            continue
                        return None

                    result = response.json()
                    logger.info(f"Попытка {attempt}/{max_retries}: Ответ от OpenRouter получен")
                    logger.debug(f"Полный ответ: {result}")

                    # Проверяем наличие choices
                    if not result.get("choices"):
                        logger.warning(f"Попытка {attempt}/{max_retries}: В ответе нет choices")
                        if attempt < max_retries:
                            await asyncio.sleep(2 * attempt)
                            continue
                        return None

                    message = result["choices"][0]["message"]

                    # Проверяем наличие сгенерированных изображений
                    if message.get("images"):
                        logger.info(f"Попытка {attempt}/{max_retries}: Получено изображений: {len(message['images'])}")

                        # Берем первое изображение
                        image_data = message["images"][0]
                        image_url_from_response = image_data.get("image_url", {}).get("url", "")

                        if image_url_from_response.startswith("data:image"):
                            # Это base64 data URL
                            # Формат: data:image/png;base64,<base64_data>
                            if "base64," in image_url_from_response:
                                base64_data = image_url_from_response.split("base64,")[1]
                                decoded_image = base64.b64decode(base64_data)
                                logger.info(f"Попытка {attempt}/{max_retries}: Изображение успешно декодировано из base64")
                                return decoded_image
                            else:
                                logger.warning(f"Попытка {attempt}/{max_retries}: Base64 data не найдена в URL")
                                if attempt < max_retries:
                                    await asyncio.sleep(2 * attempt)
                                    continue
                                return None
                        else:
                            logger.warning(
                                f"Попытка {attempt}/{max_retries}: Неожиданный формат URL изображения: "
                                f"{image_url_from_response[:50] if image_url_from_response else 'empty'}"
                            )
                            if attempt < max_retries:
                                await asyncio.sleep(2 * attempt)
                                continue
                            return None
                    else:
                        logger.warning(f"Попытка {attempt}/{max_retries}: В ответе нет сгенерированных изображений")
                        logger.debug(f"Message content: {message.get('content')}")
                        # Если это не последняя попытка, ждем и пробуем снова
                        if attempt < max_retries:
                            await asyncio.sleep(2 * attempt)
                            continue
                        return None

            except httpx.TimeoutException:
                logger.warning(f"Попытка {attempt}/{max_retries}: Таймаут при обращении к OpenRouter API")
                if attempt < max_retries:
                    await asyncio.sleep(2 * attempt)
                    continue
                logger.error(f"Все {max_retries} попытки завершились таймаутом")
                return None
            except Exception as e:
                logger.warning(f"Попытка {attempt}/{max_retries}: Ошибка при генерации изображения: {e}")
                if attempt < max_retries:
                    await asyncio.sleep(2 * attempt)
                    continue
                logger.error(f"Все {max_retries} попытки завершились ошибкой: {e}", exc_info=True)
                return None

        # Если дошли сюда, все попытки исчерпаны
        logger.error(f"Не удалось сгенерировать изображение после {max_retries} попыток")
        return None

    async def process_user_image(
        self, bot, photo: PhotoSize
    ) -> Optional[BufferedInputFile]:
        """
        Обработать изображение пользователя и вернуть сгенерированное

        Args:
            bot: Экземпляр бота
            photo: Фотография от пользователя

        Returns:
            BufferedInputFile: Готовое к отправке изображение или None
        """
        try:
            # Скачиваем исходное изображение
            image_bytes = await self.download_photo(bot, photo)

            # Генерируем новое изображение
            generated_bytes = await self.generate_image(image_bytes)

            if generated_bytes:
                # Создаем BufferedInputFile для отправки в Telegram
                return BufferedInputFile(
                    file=generated_bytes,
                    filename="generated_image.jpg"
                )

            return None

        except Exception as e:
            logger.error(f"Ошибка при обработке изображения: {e}")
            return None


# Глобальный экземпляр сервиса
openrouter_service = OpenRouterService()
