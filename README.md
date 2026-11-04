# ARM OpenWrt 云编译

此仓库从 [openwrt-build-x86](https://github.com/licong87/openwrt-build-x86) 拆分，使用 LibWrt 25.12-nss 源码编译 IPQ60xx 固件。

在 Actions 中选择所需的独立工作流，点击 Run workflow，只编译选中的配置：

- `nowifi-ress01`
- `nowifi-znm2`

编译完成后在本仓库 Releases 下载固件。两个编译工作流仅手动触发，不自动定时编译（实际完成时间取决于排队和编译结果）。每种配置发布成功后立即清理该类型的旧 Release 及标签，各保留最新一份，合计两份；编译或发布失败时保留上次成功版本。Auto-Clean 默认保持禁用；手动启用并运行后可按固件类型各保留最新一份正式 Release，并清理历史运行记录。

构建核心和公共脚本与 x86 仓库分别维护；ARM 保留设备原有网口定义；主路由 PPPoE IPv6 和插件初始选项与 x86 对齐。软件包和 feeds 均随上游更新，实际刷机前请确认镜像对应设备并备份配置。

## ARM 主路由默认设置

`nowifi-ress01` 默认后台地址为 `192.168.10.1`；`nowifi-znm2` 保持原有默认后台地址 `192.168.1.1`。两种构建保留 Nikki，移除 HomeProxy、OpenClash 和 dae 的配置项。

首次启动（或保留配置升级后首次启动）设置 WAN IPv6 自动获取与前缀委派、LAN /64、关闭 LAN 前缀委派、RA/SLAAC、存在可用前缀时通告默认路由器、过滤 dnsmasq AAAA 查询，并停用 LAN DHCPv6 和 RA IPv6 DNS。仅停用与 WAN 绑定同一设备的默认 DHCPv6 wan6；不设置拨号账号或更改网口定义。脚本会更改已有 IPv6 配置，升级前请备份并核查；实际 IPv6 连接取决于运营商。

Nikki 默认 TUN 和 IPv6 接管，API 和代理认证密码均为 123456；选择配置后自行启用，勿将 API 开放至公网。ZeroTier 默认网络勾选启用、管理路由、入站、转发和伪装，网络 ID 留空，预置网络的转发和伪装接口为 `br-lan`，全局服务需自行启用。UPnP 和 Vlmcsd 默认开启；UPnP 使用源码支持的私有 IPv4 选项。服务包默认值对全新安装有效，保留配置升级不会覆盖现有插件配置。

Release 标题及发布文件名包含北京时间戳（年月日_时分秒）；profiles.json 与 sha256sums 保持引用和校验一致。

ZeroTier 全局默认保持关闭；监听端口为 9993，本地配置文件路径为 `/etc/zerotier.conf`，持久配置目录为 `/etc/zerotier`，允许入站，不启用复制配置目录。首次启用时由设备生成密钥。

Argon 主题默认启用必应每日壁纸，在线获取失败时回退到内置背景。保留配置升级时沿用已有壁纸选择；已有设备可在 Argon 设置中将“壁纸来源”改为 Bing 并保存应用。
