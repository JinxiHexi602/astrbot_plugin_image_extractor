import re
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api.message_components import Plain, Image

@register("astrbot_plugin_image_extractor", "YourName", "1.0.0", "只提取并发送Markdown中的图片，丢弃文字内容")
class ImageExtractorPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    @filter.on_decorating_result()
    async def extract_markdown_images(self, event: AstrMessageEvent):
        # 获取大模型即将发出的消息链
        result = event.get_result()
        if not result or not result.chain:
            return

        # 1. 提取所有图片 URL
        new_images = []
        # 匹配 ![alt](url)
        pattern = r'!\[.*?\]\((https?://[^\s\)]+)\)'
        
        for component in result.chain:
            if isinstance(component, Plain):
                # 从纯文本中寻找所有符合 Markdown 格式的图片链接
                urls = re.findall(pattern, component.text)
                for url in urls:
                    # 顺便兼容处理 grok2api 可能产生的双斜杠问题
                    safe_url = url.replace("icu//images", "icu/images")
                    new_images.append(Image.fromURL(safe_url))
            elif isinstance(component, Image):
                # 如果消息链里本来就有图片对象，也保留下来
                new_images.append(component)

        # 2. 如果找到了任何图片，则直接覆盖原有的消息链
        # 这样就会导致原本的 Plain(文字) 被丢弃，只剩下图片
        if new_images:
            result.chain = new_images
