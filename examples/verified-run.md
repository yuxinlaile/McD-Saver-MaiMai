# 真实运行验证记录（verified-run）

> 本文件用于留档**真实 Token 环境**下四步检查的运行证据——这是项目
> 「真实性即信任」文化的一部分。格式借鉴 mcd-budget-meal 的 verified-run 实践。
>
> ⚠️ 提交前务必脱敏：门店编码可保留、**Token 与手机号绝对不能出现**。

## 如何生成一份验证记录

1. 配置 Token 后验证连通性：

   ```bash
   python scripts/mcd.py check
   ```

2. 按顺序执行四步检查并保存输出（原样保存，不美化）：

   ```bash
   python scripts/mcd.py call available-coupons --raw > run-available.json
   python scripts/mcd.py call query-my-coupons --raw > run-coupons.json
   python scripts/mcd.py call query-meals --args '{"storeCode": "你的门店编码"}' --raw > run-menu.json
   python scripts/mcd.py call query-my-account --raw > run-points.json
   python scripts/mcd.py call order-list --raw > run-orders.json
   ```

3. 生成体检与排程报告：

   ```bash
   python scripts/silent_cost.py report --coupons run-coupons.json \
       --orders run-orders.json --points run-points.json --probe --store-code 你的门店编码
   ```

4. 把终端输出（脱敏后）粘贴到本文件的「运行记录」节，附上日期与门店城市
   （可只写城市不写门店名）， optionally 附终端截图。

## 运行记录

<!-- 模板：真实运行后按此格式填写
### 2026-XX-XX · XX 市 · 到店取餐

- Token 状态：check 通过
- 可领券：X 张（其中 X 张菜单无法匹配，如实标注）
- 比价结论：单点 ¥XX.X → 套餐 ¥XX.X（省 XX%）
- 排程结论：名义 ¥XX.X → 可实现 ¥XX.X，注定过期 ¥XX.X
- 附件：run-*.json（脱敏后）与终端截图
-->

> 尚未留档：等待真实 Token 环境的首次运行。欢迎社区贡献者按上述步骤
> 提交你的验证记录（PR 或 Issue 附件均可）。
