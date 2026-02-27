# Licensed under the MIT License. See LICENSE file in the project root for full license information.

###########################################################################
#                           免责声明 (DISCLAIMER)                          #
# ======================================================================= #
# 1. 用途限制：本代码模板仅用于学习、研究和个人非商业用途，严禁用于以下违规场景：
#    - 违反Telegram API使用条款的行为（如批量发送消息、批量加群/拉人、刷屏、骚扰用户）；
#    - 传播违法信息、诈骗、广告营销、侵犯他人隐私等违反法律法规的行为；
#    - 任何损害Telegram平台或第三方合法权益的行为。
#
# 2. 合规要求：使用者必须严格遵守《Telegram API使用条款》(https://core.telegram.org/api/terms)
#    及使用者所在地的所有法律法规，自行承担合规审查义务。
#
# 3. 责任豁免：
#    - 作者不对本代码模板的功能完整性、稳定性、安全性做任何明示或默示的担保；
#    - 作者不承担因使用/修改/分发本代码模板导致的任何直接/间接损失，包括但不限于：
#      Telegram账号封禁、数据泄露、法律纠纷、财产损失、商誉损失等；
#    - 使用者因违规使用本代码模板产生的一切法律责任、经济赔偿，均由使用者自行承担，
#      与代码作者无任何关联。
#
# 4. 衍生作品：基于本模板开发的衍生作品，其使用风险、合规责任均由衍生作品开发者/使用者承担，
#    作者不对衍生作品的任何行为负责。
#
# 5. 风险提示：Telegram官方有权根据使用条款限制/封禁违规账号，违规使用本模板将导致账号
#    永久封禁，且可能触发法律追责，使用者需自行评估风险。
###########################################################################
import os
import json
import logging
import asyncio
from datetime import datetime
from aiohttp import web
from telethon import TelegramClient, events, functions, types
from telethon.tl.tlobject import TLObject

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
PHONE_NUMBER = os.getenv("PHONE_NUMBER")
HTTP_PORT = int(os.getenv("HTTP_PORT", 8080))
SESSION_DIR = "/app/sessions"
SESSION_NAME = "tg_session"

# Ensure session directory exists
os.makedirs(SESSION_DIR, exist_ok=True)
session_path = os.path.join(SESSION_DIR, SESSION_NAME)

# Initialize Telegram Client
client = TelegramClient(session_path, API_ID, API_HASH)

class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, bytes):
            return list(obj)
        if isinstance(obj, TLObject):
            return obj.to_dict()
        if hasattr(obj, 'to_dict'):
            return obj.to_dict()
        return super().default(obj)

async def update_profile(**kwargs):
    """
    Custom handler for updating profile information.
    Supports: about, first_name, last_name
    """
    try:
        # Filter valid arguments for UpdateProfileRequest
        valid_args = ['about', 'first_name', 'last_name']
        request_args = {k: v for k, v in kwargs.items() if k in valid_args}
        
        if not request_args:
            return "No valid parameters provided (about, first_name, last_name)"
            
        await client(functions.account.UpdateProfileRequest(**request_args))
        return "Profile updated successfully"
    except Exception as e:
        logger.error(f"Error in update_profile: {e}")
        raise e

# Registry of custom methods that are not directly on the client object
CUSTOM_METHODS = {
    "update_profile": update_profile
}

async def handle_call(request):
    try:
        data = await request.json()
        method_name = data.get("method")
        params = data.get("params", {})

        if not method_name:
            return web.json_response(
                {"status": "error", "error": "Method name is required"},
                status=400
            )

        logger.info(f"Received request: method={method_name}, params={params}")

        # Check if it's a custom method first
        if method_name in CUSTOM_METHODS:
            method = CUSTOM_METHODS[method_name]
            if asyncio.iscoroutinefunction(method):
                result = await method(**params)
            else:
                result = method(**params)
        elif hasattr(client, method_name):
            method = getattr(client, method_name)
            
            # Check if the method is callable
            if not callable(method):
                 return web.json_response(
                    {"status": "error", "error": f"Attribute '{method_name}' is not callable"},
                    status=400
                )

            # Execute the method
            if asyncio.iscoroutinefunction(method):
                result = await method(**params)
            else:
                result = method(**params)
        else:
            return web.json_response(
                {"status": "error", "error": f"Method '{method_name}' not found"},
                status=404
            )

        # Serialize result
        response_data = {
            "status": "success",
            "result": result
        }
        
        return web.json_response(response_data, dumps=lambda x: json.dumps(x, cls=DateTimeEncoder))

    except Exception as e:
        logger.error(f"Error executing method '{method_name}': {str(e)}", exc_info=True)
        return web.json_response(
            {"status": "error", "error": str(e)},
            status=500
        )

async def start_client():
    logger.info("Starting Telegram Client...")
    # If phone number is provided and session doesn't exist/authorized, this might trigger interactive login
    # But in non-interactive mode (docker without -it), it might fail if auth is needed.
    # The user is expected to run with -it for the first time.
    await client.start(phone=PHONE_NUMBER)
    logger.info("Telegram Client started and authorized.")

async def stop_client():
    await client.disconnect()

async def init_app():
    app = web.Application()
    app.router.add_post('/api/call', handle_call)
    return app

async def main():
    # Start Telegram Client
    await start_client()
    
    # Start Web Server
    app = await init_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', HTTP_PORT)
    
    logger.info(f"Starting HTTP server on port {HTTP_PORT}")
    await site.start()
    
    # Keep the application running
    try:
        # Wait until the client is disconnected (which usually happens on stop)
        await client.run_until_disconnected()
    except Exception as e:
        logger.error(f"Client disconnected with error: {e}")
    finally:
        await runner.cleanup()

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        pass
