import re
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star
from astrbot.api.message_components import Plain, Image

class ImageExtractorPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    # 使用 on_decorating_result，只在最终发送前进行“装饰”篡改，绝不干扰框架原有发送流程
    @filter.on_decorating_result()
    async def extract_markdown_images(self, event: AstrMessageEvent):
        result = event.get_result()
        # 确保存在将要发送的消息链
        if not result or not result.chain:
            return

        # Markdown 图片匹配正则
        pattern = r'!\[.*?\]\((https?://[^\s\)]+)\)'
        image_urls =
