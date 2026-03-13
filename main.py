import re
from astrbot.api.event import filter, AstrMessageEvent, MessageChain
from astrbot.api.star import Context, Star
from astrbot.api import logger
from astrbot.api.message_components import Image, Plain

class ImageExtractorPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    # 拦截大模型返回
    @filter.on_llm_response()
    async def extract_markdown_images(self, event: AstrMessageEvent, *args, **kwargs):
        """
        拦截大模型返回，提取 Markdown 图片并转为原生图片发送
        使用 *args, **kwargs 完美兼容 AstrBot v4 最新版(event, req, resp) 和老版本(event, resp)
        """
        # 1. 动态从参数中找出 LLMResponse 对象
        resp = None
        for arg in args:
            if hasattr(arg, "completion_text"):
                resp = arg
                break
        if not resp and "resp" in kwargs:
            resp = kwargs["resp"]

        # 确保成功获取到返回值，且文本不为空
        if not resp or not getattr(resp, "completion_text", None):
            return

        text = resp.completion_text

        # 2. 正则表达式匹配大模型返回的图片格式： ![描述](http(s)://链接)
        pattern = r'!\[(.*?)\]\((https?://[^\s\)]+)\)'
        matches = re.findall(pattern, text)
        
        if not matches:
            return  # 没有匹配到图片，直接放行，交给后续流程
            
        logger.info(f"拦截到包含 Markdown 的回复，共 {len(matches)} 张图片。正在转换为原生图片发送...")

        # 3. 将图片 Markdown 语法从文本中移除，保留剩余的纯文本
        clean_text = re.sub(pattern, '', text).strip()
        
        # ⚠️ 【关键】清空大模型原本的返回结果。以防 AstrBot 顺着原流程再发一遍纯文本
        resp.completion_text = ""

        # 4. 构建图文消息链并主动发送
        msg_chain = MessageChain()
        
        # 如果去除了图片后还有文字（比如 "I generated images with the prompt..."）
        if clean_text:
            msg_chain.chain.append(Plain(clean_text + "\n"))
            
        # 把提取到的所有图片添加到消息链中
        for alt_text, url in matches:
            # 💡 顺手修复 grok2api 返回双斜杠 (icu//images) 的隐患，以防底层库下载失败
            url = url.replace("icu//images", "icu/images")
            msg_chain.chain.append(Image.fromURL(url))

        # 越过原先的流程，调用 event.send 主动发送处理好的图文消息
        await event.send(msg_chain)
