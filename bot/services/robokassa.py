"""Сервис для работы с Robokassa"""
from decimal import Decimal
from typing import Optional

from robokassa import HashAlgorithm, Robokassa

from bot.config import config
from bot.logger import logger


class RobokassaService:
    """Класс для работы с платежной системой Robokassa"""

    def __init__(self):
        """Инициализация сервиса Robokassa"""
        self.robokassa = Robokassa(
            merchant_login=config.robokassa.merchant_login,
            password1=config.robokassa.password1,
            password2=config.robokassa.password2,
            is_test=config.robokassa.test_mode,
            algorithm=HashAlgorithm.md5,
        )

    def create_payment_link(
        self, invoice_id: str, amount: Decimal, description: str
    ) -> tuple[str, int]:
        """
        Создать ссылку на оплату

        Args:
            invoice_id: Уникальный ID платежа (UUID)
            amount: Сумма платежа
            description: Описание платежа

        Returns:
            Кортеж (ссылка на оплату, числовой inv_id)
        """
        try:
            # Генерируем числовой inv_id из UUID для передачи в Robokassa
            # Берем последние 10 цифр от hash UUID (чтобы поместился в INT)
            numeric_inv_id = abs(hash(invoice_id)) % 10**9

            # Создаем чек для 54-ФЗ
            receipt = {
                "sno": "usn_income",  # Система налогообложения: УСН доход
                "items": [
                    {
                        "name": description,  # Название товара
                        "quantity": 1,  # Количество
                        "sum": float(amount),  # Сумма
                        "payment_method": "full_payment",  # Полная оплата
                        "payment_object": "service",  # Предмет расчета: услуга
                        "tax": "none"  # Без НДС
                    }
                ]
            }

            # Создаем ссылку на оплату
            # Используем дополнительный параметр shp_payment_id для передачи UUID
            payment_response = self.robokassa.generate_open_payment_link(
                out_sum=float(amount),
                inv_id=numeric_inv_id,  # Числовой ID для Robokassa API
                inv_desc=description,
                receipt=receipt,  # Чек для 54-ФЗ
                shp_payment_id=invoice_id  # Передаем UUID через дополнительный параметр
            )

            # Извлекаем URL из RobokassaResponse объекта
            payment_url = payment_response.url

            logger.info(
                f"Создана ссылка на оплату: {invoice_id}, "
                f"inv_id: {numeric_inv_id}, сумма: {amount}"
            )
            return payment_url, numeric_inv_id

        except Exception as e:
            logger.error(f"Ошибка при создании ссылки на оплату: {e}", exc_info=True)
            raise

    async def check_payment_status(self, invoice_id: str) -> Optional[str]:
        """
        Проверить статус платежа через API Robokassa

        Args:
            invoice_id: ID платежа

        Returns:
            Статус платежа: "success", "pending", "failed" или None при ошибке
        """
        try:
            logger.info(f"Проверка статуса платежа через API: {invoice_id}")

            # Получаем детали платежа из Robokassa
            payment_details = await self.robokassa.get_payment_details(
                inv_id=int(invoice_id)
            )

            if payment_details:
                # Проверяем статус платежа
                # В Robokassa возможные статусы:
                # - StateCode: 5, 10, 50, 60, 80, 100
                # 5 - ожидает оплаты
                # 10 - оплачен, ожидает подтверждения
                # 50 - оплачен и подтвержден
                # 60 - возврат
                # 80 - отменен
                # 100 - частичный возврат

                state_code = payment_details.state.value

                if state_code in [50, 100]:  # Оплачен или частично возвращен
                    logger.info(f"Платеж {invoice_id} успешно оплачен (StateCode: {state_code})")
                    return "success"
                elif state_code in [5, 10]:  # Ожидает оплаты или подтверждения
                    logger.info(f"Платеж {invoice_id} ожидает (StateCode: {state_code})")
                    return "pending"
                elif state_code in [60, 80]:  # Возврат или отменен
                    logger.info(f"Платеж {invoice_id} отменен (StateCode: {state_code})")
                    return "failed"
                else:
                    logger.warning(f"Неизвестный статус платежа {invoice_id}: StateCode={state_code}")
                    return "pending"
            else:
                logger.warning(f"Не удалось получить детали платежа {invoice_id}")
                return None

        except Exception as e:
            logger.error(f"Ошибка при проверке статуса платежа: {e}", exc_info=True)
            return None

    def verify_signature(
        self, out_sum: str, inv_id: str, signature: str
    ) -> bool:
        """
        Проверить подпись от Robokassa

        Args:
            out_sum: Сумма платежа
            inv_id: ID платежа
            signature: Подпись

        Returns:
            True если подпись верна
        """
        try:
            is_valid = self.robokassa.check_signature_result(
                out_sum=out_sum,
                inv_id=inv_id,
                signature=signature
            )

            if is_valid:
                logger.info(f"Подпись платежа {inv_id} верна")
            else:
                logger.warning(f"Неверная подпись платежа {inv_id}")

            return is_valid

        except Exception as e:
            logger.error(f"Ошибка при проверке подписи: {e}", exc_info=True)
            return False


# Глобальный экземпляр сервиса
robokassa_service = RobokassaService()
