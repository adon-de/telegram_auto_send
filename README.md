基于 Docker 的 Telegram 常驻服务，通过 HTTP API 提供通用的 Telegram 操作接口。
## 1. 环境准备

- **Docker**: 20.10+
- **Docker Compose**: 1.29+
- **Telegram API 凭据**: 从 [my.telegram.org](https://my.telegram.org) 获取 `API_ID` 和 `API_HASH`。

部署telegram持久化服务
1. 将 `tg-service-image.tar` 上传到docker。
2.创建容器
3. 配置容器变量

API_ID=1234567
API_HASH=your_api_hash_here
PHONE_NUMBER=+8613800000000
HTTP_PORT=8080
TZ=Asia/Shanghai

Volumes (持久化)
**重要**：必须持久化 `/app/sessions`，否则重启后需要重新登录。
- 点击 **map additional volume**
- **container**: `/app/sessions`
- **volume**: 选择 **Bind** (映射到宿主机路径) 或 **Volume** (Docker 命名卷，如 `tg_session_vol`)。
  - 推荐 **Bind**: `/path/to/your/sessions` -> `/app/sessions` (方便备份)
  - 也可以用 **Volume**: `tg_session_data` -> `/app/sessions` (由 Docker 自动管理)

修改启动命令法 (推荐)**
1. 在创建/编辑容器时，找到 **Command & logging** 选项卡。
2. 将 **Command** 覆盖为：`tail -f /dev/null` (让容器空转)。
3. **Deploy** 部署并启动容器。
4. 点击容器的 **>_ Console** > **Connect**。
5. 在终端执行 `python main.py`。
6. 按提示输入手机号和验证码，直到看到 "Telegram Client started"。
7. 按 `Ctrl+C` 停止脚本。
8. 回到容器配置，**清空 Command** (恢复默认)，重新 **Deploy**。

青龙面板脚本配置

本项目的 `ql_send_msg.py` 专为青龙面板设计，支持批量发送消息。
必填项：TG 服务地址
- **名称**: `TG_SERVICE_URL`
- **值**: `http://tg-listener:8080/api/call` (如果青龙和 TG 服务在同一 Docker 网络)
  - 如果不在同一网络，请填写 TG 服务的局域网 IP:端口。
