"""Webhook сервер для обработки платежей Robokassa"""
import asyncio
from typing import Optional
from decimal import Decimal

from aiohttp import web
import logging

from bot.config import config
from bot.database import get_db_session
from bot.repositories.payment_repository import PaymentRepository
from bot.repositories.user_repository import UserRepository
from bot.services.robokassa import robokassa_service
from bot.logger import logger


async def handle_robokassa_result(request: web.Request) -> web.Response:
    """
    Обработчик Result URL от Robokassa

    Robokassa отправляет GET-запрос на Result URL после успешной оплаты
    с параметрами: OutSum, InvId, SignatureValue

    Args:
        request: HTTP запрос от Robokassa

    Returns:
        HTTP ответ (OK{InvId} при успехе)
    """
    try:
        # Получаем параметры из запроса
        params = request.rel_url.query

        out_sum = params.get('OutSum')
        inv_id = params.get('InvId')
        signature = params.get('SignatureValue')
        payment_id = params.get('shp_payment_id')  # Наш UUID платежа

        logger.info(
            f"Получен Result URL от Robokassa: "
            f"OutSum={out_sum}, InvId={inv_id}, PaymentId={payment_id}"
        )

        # Проверяем наличие всех необходимых параметров
        if not all([out_sum, signature, payment_id]):
            logger.warning("Отсутствуют обязательные параметры в Result URL")
            return web.Response(text="Missing required parameters", status=400)

        # Проверяем подпись
        is_valid = robokassa_service.verify_signature(
            out_sum=out_sum,
            inv_id=inv_id,
            signature=signature
        )

        if not is_valid:
            logger.warning(f"Неверная подпись для платежа {inv_id}")
            return web.Response(text="Invalid signature", status=403)

        # Обрабатываем платеж
        async with get_db_session() as session:
            payment_repo = PaymentRepository(session)
            user_repo = UserRepository(session)

            # Находим платеж по UUID (shp_payment_id)
            import uuid
            try:
                payment_uuid = uuid.UUID(payment_id)
            except (ValueError, AttributeError):
                logger.error(f"Неверный формат payment_id: {payment_id}")
                return web.Response(text="Invalid payment_id", status=400)

            payment = await payment_repo.get_payment_by_id(payment_uuid)

            if not payment:
                logger.error(f"Платеж с id={payment_id} не найден")
                return web.Response(text="Payment not found", status=404)

            # Проверяем, что платеж еще не обработан
            if payment.payment_status == "success":
                logger.info(f"Платеж {payment.id} уже обработан")
                return web.Response(text=f"OK{inv_id}")

            # Проверяем, что inv_id совпадает (если уже установлен)
            if payment.invoice_id and inv_id and str(payment.invoice_id) != str(inv_id):
                logger.warning(
                    f"Несоответствие inv_id: в БД {payment.invoice_id}, "
                    f"от Robokassa {inv_id}"
                )

            # Обновляем статус платежа
            await payment_repo.update_payment_status(payment.id, "success")

            # Зачисляем генерации (если еще не зачислены)
            if not payment.credited:
                success = await user_repo.update_generations(
                    payment.telegram_id,
                    payment.generations
                )

                if success:
                    await payment_repo.mark_as_credited(payment.id)
                    logger.info(
                        f"Платеж {payment.id} успешно обработан: "
                        f"зачислено {payment.generations} генераций "
                        f"пользователю {payment.telegram_id}"
                    )
                else:
                    logger.error(
                        f"Не удалось зачислить генерации по платежу {payment.id}"
                    )

            # Отправляем OK ответ Robokassa
            return web.Response(text=f"OK{inv_id}")

    except Exception as e:
        logger.error(f"Ошибка при обработке Result URL: {e}", exc_info=True)
        return web.Response(text="Internal server error", status=500)


async def handle_robokassa_success(request: web.Request) -> web.Response:
    """
    Обработчик Success URL (страница успешной оплаты)

    Robokassa перенаправляет пользователя на Success URL после оплаты

    Args:
        request: HTTP запрос

    Returns:
        HTML страница с сообщением об успехе
    """
    params = request.rel_url.query
    inv_id = params.get('InvId', 'неизвестен')

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Оплата успешна</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{
                font-family: Arial, sans-serif;
                text-align: center;
                padding: 50px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
            }}
            .container {{
                background: white;
                color: #333;
                padding: 40px;
                border-radius: 10px;
                max-width: 500px;
                margin: 0 auto;
                box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            }}
            h1 {{ color: #28a745; }}
            .emoji {{ font-size: 64px; margin: 20px 0; }}
            .button {{
                display: inline-block;
                padding: 15px 30px;
                margin-top: 20px;
                background: #667eea;
                color: white;
                text-decoration: none;
                border-radius: 5px;
                font-weight: bold;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="emoji">✅</div>
            <h1>Платеж успешно завершен!</h1>
            <p><strong>ID платежа:</strong> {inv_id}</p>
            <p>Генерации будут зачислены на ваш счёт в течение нескольких минут.</p>
            <p>Вернитесь в бот и нажмите кнопку <strong>"Проверить платеж"</strong> для зачисления генераций.</p>
            <a href="https://t.me/{config.bot.bot_username}" class="button">
                Вернуться в бот
            </a>
        </div>
    </body>
    </html>
    """

    return web.Response(text=html, content_type='text/html')


async def handle_robokassa_fail(request: web.Request) -> web.Response:
    """
    Обработчик Fail URL (страница отмененной оплаты)

    Args:
        request: HTTP запрос

    Returns:
        HTML страница с сообщением об ошибке
    """
    params = request.rel_url.query
    inv_id = params.get('InvId', 'неизвестен')

    # Обновляем статус платежа на failed
    try:
        async with get_db_session() as session:
            payment_repo = PaymentRepository(session)
            payment = await payment_repo.get_payment_by_invoice_id(inv_id)

            if payment:
                await payment_repo.update_payment_status(payment.id, "failed")
                logger.info(f"Платеж {payment.id} отменен")
    except Exception as e:
        logger.error(f"Ошибка при обновлении статуса платежа: {e}")

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Оплата отменена</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{
                font-family: Arial, sans-serif;
                text-align: center;
                padding: 50px;
                background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
                color: white;
            }}
            .container {{
                background: white;
                color: #333;
                padding: 40px;
                border-radius: 10px;
                max-width: 500px;
                margin: 0 auto;
                box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            }}
            h1 {{ color: #dc3545; }}
            .emoji {{ font-size: 64px; margin: 20px 0; }}
            .button {{
                display: inline-block;
                padding: 15px 30px;
                margin-top: 20px;
                background: #667eea;
                color: white;
                text-decoration: none;
                border-radius: 5px;
                font-weight: bold;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="emoji">❌</div>
            <h1>Оплата отменена</h1>
            <p><strong>ID платежа:</strong> {inv_id}</p>
            <p>Платеж не был завершен. Вы можете попробовать снова.</p>
            <a href="https://t.me/{config.bot.bot_username}" class="button">
                Вернуться в бот
            </a>
        </div>
    </body>
    </html>
    """

    return web.Response(text=html, content_type='text/html')


async def handle_health(request: web.Request) -> web.Response:
    """Проверка здоровья сервера"""
    return web.Response(text="OK")


def create_app() -> web.Application:
    """Создание приложения aiohttp"""
    app = web.Application()

    # Добавляем роуты
    app.router.add_get('/robokassa/result', handle_robokassa_result)
    app.router.add_post('/robokassa/result', handle_robokassa_result)
    app.router.add_get('/robokassa/success', handle_robokassa_success)
    app.router.add_get('/robokassa/fail', handle_robokassa_fail)
    app.router.add_get('/health', handle_health)

    return app


async def main():
    """Запуск webhook сервера"""
    app = create_app()

    # Получаем порт из переменных окружения или используем 8080 по умолчанию
    import os
    port = int(os.getenv('WEBHOOK_PORT', '8080'))
    host = os.getenv('WEBHOOK_HOST', '0.0.0.0')

    logger.info(f"Запуск webhook сервера на {host}:{port}")
    logger.info(f"Result URL: http://{host}:{port}/robokassa/result")
    logger.info(f"Success URL: http://{host}:{port}/robokassa/success")
    logger.info(f"Fail URL: http://{host}:{port}/robokassa/fail")

    runner = web.AppRunner(app)
    await runner.setup()

    site = web.TCPSite(runner, host, port)
    await site.start()

    logger.info("Webhook сервер запущен")

    # Держим сервер запущенным
    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        logger.info("Остановка webhook сервера...")
    finally:
        await runner.cleanup()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Webhook сервер остановлен")
