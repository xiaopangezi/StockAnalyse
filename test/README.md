# 测试目录说明

本目录包含StockAnalyse项目的所有测试代码，采用标准的Python单元测试框架。

## 目录结构

```
test/
├── __init__.py              # 测试包初始化文件
├── conftest.py              # pytest配置文件
├── test_pdf_parser.py       # PDF解析器测试文件
├── run_tests.py             # 测试运行脚本
└── README.md                # 本说明文件
```

## 测试文件说明

### 1. test_pdf_parser.py
PDF解析器的主要测试文件，包含以下测试类：

- **TestPdfOutlineNode**: 测试目录节点类
  - 节点创建和属性设置
  - 树结构构建
  - 字典转换
  - 章节ID生成

- **TestPdfParserLogic**: 测试PDF解析器逻辑功能
  - 兄弟节点查找
  - 父级兄弟节点查找
  - 下一小节标题获取
  - 页码计算逻辑验证

- **TestPdfParserEdgeCases**: 测试边界情况
  - 单页章节处理
  - 空子节点处理
  - 根节点处理

- **TestPdfParserIntegration**: 测试集成功能
  - 模拟PDF解析
  - 依赖注入测试

## 运行测试

### 方法1: 使用unittest（推荐）

```bash
# 在test目录下运行
cd test
python test_pdf_parser.py

# 或者在项目根目录运行
python -m test.test_pdf_parser
```

### 方法2: 使用测试运行脚本

```bash
# 使用unittest运行器（默认）
python test/run_tests.py

# 使用pytest运行器
python test/run_tests.py --runner pytest

# 运行特定测试
python test/run_tests.py --runner pytest --test "test_node_creation"
```

### 方法3: 使用pytest（需要安装pytest）

```bash
# 安装pytest
pip install pytest

# 运行所有测试
pytest test/ -v

# 运行特定测试文件
pytest test/test_pdf_parser.py -v

# 运行特定测试方法
pytest test/test_pdf_parser.py::TestPdfOutlineNode::test_node_creation -v

# 运行包含特定关键词的测试
pytest test/ -k "node" -v
```

## 测试覆盖率

要生成测试覆盖率报告，需要安装coverage：

```bash
# 安装coverage
pip install coverage

# 运行测试并生成覆盖率报告
coverage run -m pytest test/
coverage report
coverage html  # 生成HTML报告
```

## 测试最佳实践

### 1. 测试命名规范
- 测试类以`Test`开头
- 测试方法以`test_`开头
- 测试方法名应该清晰描述测试内容

### 2. 测试结构
- 使用`setUp()`方法准备测试数据
- 每个测试方法只测试一个功能点
- 使用断言验证测试结果

### 3. 模拟和依赖
- 使用`unittest.mock`模拟外部依赖
- 避免测试依赖实际的文件系统或网络

### 4. 测试数据
- 测试数据应该放在`test/data/`目录下
- 使用相对路径引用测试数据

## 添加新测试

### 1. 为新功能添加测试
```python
def test_new_feature(self):
    """测试新功能"""
    # 准备测试数据
    test_data = "测试数据"
    
    # 执行被测试的功能
    result = self.parser.new_feature(test_data)
    
    # 验证结果
    self.assertEqual(result, "期望结果")
```

### 2. 为新类添加测试类
```python
class TestNewClass(unittest.TestCase):
    """测试新类"""
    
    def setUp(self):
        """测试前的准备工作"""
        self.instance = NewClass()
    
    def test_method(self):
        """测试方法"""
        # 测试代码
        pass
```

## 故障排除

### 常见问题

1. **导入错误**: 确保项目根目录在Python路径中
2. **依赖缺失**: 安装所需的测试依赖包
3. **路径问题**: 使用相对路径或绝对路径引用测试文件

### 调试技巧

1. 使用`pytest -s`显示print输出
2. 使用`pytest --pdb`在失败时进入调试器
3. 使用`pytest -x`在第一个失败时停止

## 持续集成

测试可以集成到CI/CD流程中：

```yaml
# GitHub Actions示例
- name: Run Tests
  run: |
    python -m pytest test/ -v --tb=short
    python -m coverage run -m pytest test/
    python -m coverage report
```

## 联系方式

如有测试相关问题，请：
1. 检查测试日志和错误信息
2. 查看相关测试代码
3. 提交Issue描述问题
