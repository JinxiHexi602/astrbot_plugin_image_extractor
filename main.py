import re
from astrbot.api.event import filter, AstrMessageEvent, MessageChain
from astrbot.api.star import Context, Star
from astrbot.api import logger
from astrbot.api.provider import LLMResponse
from astrbot.api.message_components import Image, Plain

class ImageExtractorPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    # 使用 on_llm_response 钩子，可以在文本变成消息之前进行拦截和篡改
    @filter.on_llm_response()
    async def extract_markdown_images(self, event: AstrMessageEvent, resp: LLMResponse):
        """
        拦截大模型返回，提取 Markdown 图片并转为原生图片发送
        """
        if not resp or not resp.completion_text:
            return

        text = resp.completion_text

        # 正则表达式匹配大模型返回的图片格式： ![描述](http(s)://链接)
        pattern = r'!\[(.*?)\]\((https?://[^\s\)]+)\)'
        
        # 查找所有图片（返回格式为 [(描述, 链接), ...] 的列表）
        matches = re.findall(pattern, text)
        
        if not matches:
            return  # 如果没有匹配到任何图片，直接放行给框架原本的流程处理
            
        logger.info(f"拦截到包含 Markdown 的回复，共 {len(matches)} 张图片。正在转换为原生图片发送...")

        # 将图片 Markdown 语法从文本中移除，得到剩下的纯文本
        clean_text = re.sub(pattern, '', text).strip()
        
        # ⚠️ 【关键】清空大模型原本的返回结果。
        # 因为我们要接管发送过程，如果这里不清空，AstrBot 会顺着原流程再发一遍没图片的纯文本
        resp.completion_text = ""

        # 构建一个新的图文消息链
        msg_chain = MessageChain()
        
        # 如果去除了图片后还有文字（比如 "I generated images with the prompt..."）
        if clean_text:
            msg_chain.chain.append(Plain(clean_text + "\n"))
            
        # 把提取到的图片添加到消息链中
        for alt_text, url in matches:
            # 💡 这里顺手帮你修复了你日志中 grok2api 返回双斜杠 (icu//images) 的 Bug，以防底层库下载失败
            url = url.replace("icu//images", "icu/images")
            # 将 http 链接转化为 AstrBot 的原生 Image 元素
            msg_chain.chain.append(Image.fromURL(url))

        # 越过原先的流程，调用 event.send 主动发送我们构造好的图文消息
        await event.send(msg_chain)
