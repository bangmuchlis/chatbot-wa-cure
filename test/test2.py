import asyncio
from test import send_whatsapp_message

async def test_send():
    success = await send_whatsapp_message("+6285730784528", "Halo, ini tes!")
    print("Success" if success else "Failed")

asyncio.run(test_send())