"""测试配置：将 scripts 目录加入 sys.path，便于直接导入被测模块。"""
import os
import sys

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
)
