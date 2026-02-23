import ast

# 测试修复后的事件监听器代码
try:
    with open('main.py', 'r', encoding='utf-8') as f:
        code = f.read()
    
    # 检查是否有旧的错误装饰器
    if '@filter.on_message()' in code:
        print("❌ 发现旧的 @filter.on_message() 装饰器")
    else:
        print("✅ 未发现旧的 @filter.on_message() 装饰器")
    
    # 检查是否有新的事件监听器装饰器
    if '@filter.event_message_type(filter.EventMessageType.ALL)' in code:
        print("✅ 发现正确的事件监听器装饰器")
    else:
        print("❌ 未发现正确的事件监听器装饰器")
    
    # 语法检查
    ast.parse(code)
    print("✅ 语法正确")
    print("✅ 插件应该可以正常加载了")
    
except SyntaxError as e:
    print(f"❌ 语法错误: {e}")
    print(f"错误位置: 行 {e.lineno}, 列 {e.offset}")
except Exception as e:
    print(f"❌ 其他错误: {e}")