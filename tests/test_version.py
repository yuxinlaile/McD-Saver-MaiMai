"""version.py 自定义版本递增规则测试（z.x.y：y≤3、x≤6）。

规则：每次发布先递增 y；y>3 进位到 x+1 并 y=0；x>6 进位到 z+1 并 x、y 归零。
历史过渡版本（分量超限，如 1.7.4）按归一化处理：归一化结果即下一版本。
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

from version import VersionError, next_version, normalize, parse_version


class TestParse:
    def test_valid_versions(self):
        assert parse_version("0.0.0") == (0, 0, 0)
        assert parse_version("1.6.3") == (1, 6, 3)
        assert parse_version(" 2.0.0 ") == (2, 0, 0)  # 允许首尾空白

    @pytest.mark.parametrize("bad", ["", "abc", "1.2", "1.2.3.4", "-1.0.0",
                                     "1.-2.3", "1.2.-3", "v1.0.0", "1.2.x", "1..3"])
    def test_invalid_inputs_raise(self, bad):
        with pytest.raises(VersionError):
            parse_version(bad)


class TestNormalize:
    def test_legal_version_unchanged(self):
        assert normalize((1, 6, 3)) == (1, 6, 3)
        assert normalize((2, 0, 0)) == (2, 0, 0)

    def test_patch_overflow_carries_to_minor(self):
        assert normalize((1, 5, 4)) == (1, 6, 0)   # y=4 → x+1, y 重置 0
        assert normalize((1, 5, 7)) == (1, 6, 0)   # y=7 超限 → x+1, y 重置 0

    def test_minor_overflow_carries_to_major(self):
        assert normalize((1, 7, 0)) == (2, 0, 0)   # x=7 → z+1
        assert normalize((1, 7, 4)) == (2, 0, 0)   # 双重进位

    def test_zero_boundary(self):
        assert normalize((0, 0, 0)) == (0, 0, 0)


class TestNextVersion:
    @pytest.mark.parametrize("current,expected", [
        ("0.0.0", "0.0.1"),      # 最小版本起步：正常递增 y
        ("1.0.0", "1.0.1"),
        ("1.0.3", "1.1.0"),      # y=3 达上限 → 进位 x
        ("1.5.3", "1.6.0"),      # 用户示例 1
        ("1.6.0", "1.6.1"),
        ("1.6.2", "1.6.3"),
        ("1.6.3", "2.0.0"),      # 用户示例 2：y 与 x 双进位
        ("0.6.3", "1.0.0"),      # z 进位从 0 起步
        ("2.0.0", "2.0.1"),      # 新格式起点正常递增
        ("2.6.3", "3.0.0"),      # 任意 z 均按同一规则
    ])
    def test_rule_table(self, current, expected):
        assert next_version(current) == expected

    def test_transition_version_normalizes_to_next(self):
        # 1.7.4 为历史过渡版本（y=4 超限）：归一化即得下一版本 2.0.0
        assert next_version("1.7.4") == "2.0.0"

    @pytest.mark.parametrize("bad", ["", "abc", "1.2", "1.2.3.4", "1.2.-3"])
    def test_invalid_input_raises(self, bad):
        with pytest.raises(VersionError):
            next_version(bad)

    def test_result_always_in_range(self):
        # 任意合法输入的输出必满足 y≤3、x≤6
        for z in range(3):
            for x in range(8):        # 故意包含 x>6 的过渡输入
                for y in range(5):    # 故意包含 y>3 的过渡输入
                    out = next_version(f"{z}.{x}.{y}")
                    oz, ox, oy = parse_version(out)
                    assert oy <= 3 and ox <= 6
