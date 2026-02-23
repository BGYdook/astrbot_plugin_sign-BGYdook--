import ast

# 测试编译 main.py
try:
    with open('main.py', 'r', encoding='utf-8') as f:
        code = f.read()
    ast.parse(code)
    print("✅ main.py 语法检查通过")
except SyntaxError as e:
    print(f"❌ main.py 语法错误: {e}")
    print(f"错误行号: {e.lineno}")
    print(f"错误位置: {e.offset}")

# 测试编译其他文件
files = ['database.py', 'sign_manager.py', 'image_generator.py']
for file in files:
    try:
        with open(file, 'r', encoding='utf-8') as f:
            code = f.read()
        ast.parse(code)
        print(f"✅ {file} 语法检查通过")
    except SyntaxError as e:
        print(f"❌ {file} 语法错误: {e}")
        print(f"错误行号: {e.lineno}")
        print(f"错误位置: {e.offset}")

print("\n✅所有文件编译通过")