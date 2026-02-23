from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
import os
import datetime

from .database import SignDatabase
from .image_generator import ImageGenerator
from .sign_manager import SignManager

@register("astrbot_plugin_sign", "BGYdook", "一个签到插件", "1.0.0")
class SignPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.db = SignDatabase(os.path.dirname(__file__))
        self.img_gen = ImageGenerator(os.path.dirname(__file__))
        
        # 定义所有可用的功能列表
        self.available_commands = [
            "签到 - 每日签到获取金币和运势",
            "信息 - 查看个人签到信息和金币",
            "排行 - 查看签到排行榜", 
            "运势历史 - 查看历史运势记录",
            "签到帮助 - 显示此帮助信息"
        ]
        
    def get_help_info(self) -> str:
        """获取插件帮助信息，供AstrBot显示"""
        return "\n".join(self.available_commands)
        
    @filter.event_message_type(filter.EventMessageType.ALL)
    async def sign(self, event: AstrMessageEvent):
        '''每日签到 - 监听消息事件'''
        try:
            # 获取原始消息内容
            msg = event.message_str
            
            # 防止日常聊天误触发，严格匹配条件
            # 1. 去除前后空白字符
            clean_msg = msg.strip()
            
            # 2. 只响应完全等于"签到"的消息，不包含其他字符
            if clean_msg != "签到":
                return
            
            # 3. 额外的安全检查：限制消息长度（防止异常情况）
            if len(clean_msg) > 10:
                return
                
            # 执行签到逻辑
            user_id = event.get_sender_id()
            today = datetime.date.today().strftime('%Y-%m-%d')
            
            user_data = self.db.get_user_data(user_id) or {}
            
            if user_data.get('last_sign') == today:
                image_path = await self.img_gen.create_sign_image("今天已经签到过啦喵~")
                if image_path:
                    yield event.image_result(image_path)
                    if os.path.exists(image_path):
                        os.remove(image_path)
                return

            # 计算连续天数
            continuous_days = 1
            if user_data.get('last_sign') == (datetime.date.today() - datetime.timedelta(days=1)).strftime('%Y-%m-%d'):
                continuous_days = user_data.get('continuous_days', 0) + 1

            # 计算奖励
            coins_got, coins_gift = SignManager.calculate_sign_rewards(continuous_days)
            fortune_result, fortune_value = SignManager.get_fortune()

            # 更新数据
            self.db.update_user_data(
                user_id,
                total_days=user_data.get('total_days', 0) + 1,
                last_sign=today,
                continuous_days=continuous_days,
                coins=user_data.get('coins', 0) + coins_got + coins_gift,
                total_coins_gift=user_data.get('total_coins_gift', 0) + coins_gift,
                last_fortune_result=fortune_result,
                last_fortune_value=fortune_value
            )

            # 记录历史
            self.db.log_coins(user_id, coins_got, "基础签到")
            if coins_gift > 0:
                self.db.log_coins(user_id, coins_gift, "连续签到奖励")
            self.db.log_fortune(user_id, fortune_result, fortune_value)

            # 生成结果消息
            result = SignManager.format_sign_result(
                user_data, coins_got, coins_gift, 
                fortune_result, fortune_value
            )

            image_path = await self.img_gen.create_sign_image(result)
            if image_path:
                yield event.image_result(image_path)
                if os.path.exists(image_path):
                    os.remove(image_path)

        except Exception as e:
            logger.error(f"签到失败: {str(e)}")
            yield event.plain_result("签到失败了喵~请联系管理员检查日志")

    @filter.event_message_type(filter.EventMessageType.ALL)
    async def user_info(self, event: AstrMessageEvent):
        '''查询个人信息'''
        try:
            msg = event.message_str
            clean_msg = msg.strip()
            
            # 只响应完全等于"信息"的消息
            if clean_msg != "信息":
                return
                
            if len(clean_msg) > 10:
                return
                
            user_id = event.get_sender_id()
            user_data = self.db.get_user_data(user_id)
            
            if not user_data:
                yield event.plain_result("你还没有签到记录喵~快来签到吧！")
                return
                
            # 获取运势历史
            fortune_history = self.db.get_fortune_history(user_id, 1)
            latest_fortune = fortune_history[0] if fortune_history else ("暂无", 0)
            
            result = (
                f"📊 个人信息\n"
                f"💰 当前金币：{user_data.get('coins', 0)}\n"
                f"📅 累计签到：{user_data.get('total_days', 0)}天\n"
                f"🔥 连续签到：{user_data.get('continuous_days', 0)}天\n"
                f"📆 最后签到：{user_data.get('last_sign', '暂无')}\n"
                f"🔮 最近运势：{latest_fortune[0]} ({latest_fortune[1]}/100)"
            )
            
            image_path = await self.img_gen.create_sign_image(result)
            if image_path:
                yield event.image_result(image_path)
                if os.path.exists(image_path):
                    os.remove(image_path)
                    
        except Exception as e:
            logger.error(f"查询信息失败: {str(e)}")
            yield event.plain_result("查询信息失败了喵~请联系管理员检查日志")

    @filter.event_message_type(filter.EventMessageType.ALL)
    async def ranking(self, event: AstrMessageEvent):
        '''签到排行榜'''
        try:
            msg = event.message_str
            clean_msg = msg.strip()
            
            if clean_msg != "排行":
                return
                
            if len(clean_msg) > 10:
                return
                
            rankings = self.db.get_ranking(10)
            
            if not rankings:
                yield event.plain_result("暂无排行榜数据喵~")
                return
                
            result = "🏆 签到排行榜\n\n"
            for i, (user_id, coins, total_days) in enumerate(rankings, 1):
                # 获取用户昵称（这里用用户ID代替，实际应该获取昵称）
                user_name = f"用户{user_id[-4:]}"  # 显示用户ID后4位
                result += f"{i}. {user_name} - {coins}金币 ({total_days}天)\n"
                
            image_path = await self.img_gen.create_sign_image(result)
            if image_path:
                yield event.image_result(image_path)
                if os.path.exists(image_path):
                    os.remove(image_path)
                    
        except Exception as e:
            logger.error(f"查询排行失败: {str(e)}")
            yield event.plain_result("查询排行失败了喵~请联系管理员检查日志")

    @filter.event_message_type(filter.EventMessageType.ALL)
    async def sign_help(self, event: AstrMessageEvent):
        '''签到帮助'''
        try:
            msg = event.message_str
            clean_msg = msg.strip()
            
            if clean_msg != "签到帮助":
                return
                
            if len(clean_msg) > 10:
                return
                
            help_text = (
                "📖 签到帮助\n\n"
                "📝 可用指令：\n"
            )
            
            # 添加所有可用功能
            for cmd in self.available_commands:
                help_text += f"• {cmd}\n"
                
            help_text += (
                "\n💰 金币规则：\n"
                "• 基础签到：0-100金币\n"
                "• 连续签到：每天额外奖励\n"
                "• 连续7天以上：每天额外200金币\n\n"
                "🔮 运势系统：\n"
                "• 每次签到自动占卜\n"
                "• 运势分为：凶、末小吉、末吉、小吉、半吉、吉、大吉"
            )
            
            image_path = await self.img_gen.create_sign_image(help_text)
            if image_path:
                yield event.image_result(image_path)
                if os.path.exists(image_path):
                    os.remove(image_path)
                    
        except Exception as e:
            logger.error(f"显示帮助失败: {str(e)}")
            yield event.plain_result("显示帮助失败了喵~请联系管理员检查日志")

    @filter.event_message_type(filter.EventMessageType.ALL)
    async def fortune_history(self, event: AstrMessageEvent):
        '''运势历史'''
        try:
            msg = event.message_str
            clean_msg = msg.strip()
            
            if clean_msg != "运势历史":
                return
                
            if len(clean_msg) > 10:
                return
                
            user_id = event.get_sender_id()
            history = self.db.get_fortune_history(user_id, 7)  # 最近7条
            
            if not history:
                yield event.plain_result("你还没有运势记录喵~快来签到吧！")
                return
                
            result = "🔮 最近运势历史\n\n"
            for i, (result_text, value, timestamp) in enumerate(history, 1):
                result += f"{i}. {result_text} ({value}/100) - {timestamp}\n"
                
            image_path = await self.img_gen.create_sign_image(result)
            if image_path:
                yield event.image_result(image_path)
                if os.path.exists(image_path):
                    os.remove(image_path)
                    
        except Exception as e:
            logger.error(f"查询运势历史失败: {str(e)}")
            yield event.plain_result("查询运势历史失败了喵~请联系管理员检查日志")

    # ===== 额外 AstrBot 正式指令包装（用于行为统计，保留无前缀用法） =====
    # 这些命令仅用于在 AstrBot 行为列表中显示功能，不处理实际逻辑
    # 实际处理通过事件监听器完成

    @filter.command("签到")
    async def cmd_sign(self, event: AstrMessageEvent):
        """每日签到获取金币和运势"""
        # 此函数仅用于在 AstrBot 行为列表中显示功能
        # 实际处理通过事件监听器 sign() 完成
        return

    @filter.command("信息")
    async def cmd_info(self, event: AstrMessageEvent):
        """查看个人签到信息和金币"""
        # 此函数仅用于在 Astr Bot 行为列表中显示功能
        # 实际处理通过事件监听器 user_info() 完成
        return

    @filter.command("排行")
    async def cmd_ranking(self, event: AstrMessageEvent):
        """查看签到排行榜"""
        # 此函数仅用于在 AstrBot 行为列表中显示功能
        # 实际处理通过事件监听器 ranking() 完成
        return

    @filter.command("运势历史")
    async def cmd_fortune_history(self, event: AstrMessageEvent):
        """查看历史运势记录"""
        # 此函数仅用于在 AstrBot 行为列表中显示功能
        # 实际处理通过事件监听器 fortune_history() 完成
        return

    @filter.command("签到帮助")
    async def cmd_sign_help(self, event: AstrMessageEvent):
        """显示签到帮助信息"""
        # 此函数仅用于在 AstrBot 行为列表中显示功能
        # 实际处理通过事件监听器 sign_help() 完成
        return

    # 为了简洁,其他命令处理方法的实现逻辑类似,
    # 都是通过调用 db、img_gen 和 SignManager 的方法来完成功能
