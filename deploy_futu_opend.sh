#!/bin/bash
# ============================================================
# BDE-Stock - FutuOpenD 安装部署脚本
# 
# 安装富途 FutuOpenD 网关
# 用于 BDE-Stock 系统通过 futu-api 连接富途证券
#
# FutuOpenD 是富途提供的本地代理服务：
#   - 登录富途账号后，提供 Socket API 服务
#   - 默认端口: 11111
#   - 支持模拟交易(Paper Trading)和实盘交易
#   - 支持市场: 美股、港股、A股
#
# 官网: https://openapi.futunn.com
# 下载: https://openapi.futunn.com/futu-api-doc/opend/opend-cmd.html
#
# 支持平台: Linux (Ubuntu/Debian, CentOS/RHEL), macOS, Windows(WSL)
# ============================================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 配置
FUTU_OPEND_VERSION="${FUTU_OPEND_VERSION:-latest}"
FUTU_HOME="${HOME}/futu"
FUTU_OPEND_DIR="${FUTU_HOME}/opend"
FUTU_CONFIG_DIR="${FUTU_HOME}/config"
FUTU_LOG_DIR="${FUTU_HOME}/logs"

# 端口配置
FUTU_PORT=11111

# 富途账户信息（通过环境变量传入，不硬编码）
FUTU_USERNAME="${FUTU_USERNAME:-}"
FUTU_PASSWORD="${FUTU_PASSWORD:-}"
FUTU_TRADING_MODE="${FUTU_TRADING_MODE:-simulate}"  # simulate | real

print_banner() {
    echo ""
    echo "============================================================"
    echo "  BDE-Stock FutuOpenD 部署工具"
    echo "  富途证券 OpenD 网关安装与配置"
    echo "============================================================"
    echo ""
}

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# ============================================================
# 检测操作系统
# ============================================================
detect_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if [ -f /etc/debian_version ]; then
            OS_TYPE="debian"
        elif [ -f /etc/redhat-release ]; then
            OS_TYPE="redhat"
        else
            OS_TYPE="linux"
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        OS_TYPE="macos"
    elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
        OS_TYPE="windows"
    else
        OS_TYPE="unknown"
    fi
    log_info "检测到操作系统: $OS_TYPE ($OSTYPE)"
}

# ============================================================
# 安装系统依赖
# ============================================================
install_dependencies() {
    log_info "安装系统依赖..."

    case "$OS_TYPE" in
        debian)
            sudo apt-get update -qq
            sudo apt-get install -y -qq wget unzip curl
            ;;
        redhat)
            sudo yum install -y -q wget unzip curl
            ;;
        macos)
            if ! command -v brew &> /dev/null; then
                log_warn "建议安装 Homebrew: https://brew.sh"
            fi
            ;;
        *)
            log_warn "无法自动安装依赖，请确保 wget/unzip 已安装"
            ;;
    esac
}

# ============================================================
# 安装 Python futu-api 库
# ============================================================
install_futu_api() {
    log_info "安装 Python futu-api 库..."

    if python3 -c "import futu" 2>/dev/null; then
        log_info "futu-api 已安装，跳过"
        return
    fi

    # 优先使用国内镜像（中国用户更快）
    if pip3 install futu-api -i https://pypi.tuna.tsinghua.edu.cn/simple --timeout 60 2>/dev/null; then
        log_info "futu-api 安装成功 (清华镜像)"
    elif pip3 install futu-api --timeout 60 2>/dev/null; then
        log_info "futu-api 安装成功 (PyPI)"
    else
        log_error "futu-api 安装失败"
        log_warn "请手动安装: pip install futu-api"
    fi
}

# ============================================================
# 下载 FutuOpenD
# ============================================================
install_futu_opend() {
    log_info "安装 FutuOpenD..."

    mkdir -p "${FUTU_OPEND_DIR}" "${FUTU_CONFIG_DIR}" "${FUTU_LOG_DIR}"

    # 确定下载平台
    case "$OS_TYPE" in
        debian|redhat)
            PLATFORM="ubuntu20.04"
            ARCH="x86_64"
            EXT="tar.gz"
            ;;
        macos)
            PLATFORM="macos"
            ARCH="$(uname -m)"
            EXT="tar.gz"
            ;;
        windows)
            PLATFORM="windows"
            ARCH="x64"
            EXT="zip"
            ;;
        *)
            log_error "不支持的操作系统: $OS_TYPE"
            return 1
            ;;
    esac

    log_info "平台: ${PLATFORM}/${ARCH}"

    # FutuOpenD 下载页面
    DOWNLOAD_PAGE="https://openapi.futunn.com/futu-api-doc/opend/opend-cmd.html"

    # 尝试直接下载
    DOWNLOAD_URL="https://softdl.futunn.com/FutuOpenD_${FUTU_OPEND_VERSION}_${PLATFORM}_${ARCH}.${EXT}"

    TEMP_DIR=$(mktemp -d)

    log_info "尝试下载 FutuOpenD..."
    if wget -q --show-progress -O "${TEMP_DIR}/opend_download.${EXT}" "$DOWNLOAD_URL" 2>/dev/null; then
        log_info "下载成功，解压中..."
        
        if [[ "$EXT" == "tar.gz" ]]; then
            tar -xzf "${TEMP_DIR}/opend_download.${EXT}" -C "${FUTU_OPEND_DIR}" 2>/dev/null || true
        elif [[ "$EXT" == "zip" ]]; then
            unzip -q -o "${TEMP_DIR}/opend_download.${EXT}" -d "${FUTU_OPEND_DIR}" 2>/dev/null || true
        fi
        
        chmod +x "${FUTU_OPEND_DIR}"/*.sh 2>/dev/null || true
        log_info "FutuOpenD 安装完成: ${FUTU_OPEND_DIR}"
    else
        log_warn "自动下载失败，请手动下载:"
        echo ""
        echo "  ============================================================"
        echo "  手动安装步骤:"
        echo "  ============================================================"
        echo ""
        echo "  1. 访问 FutuOpenD 下载页面:"
        echo "     ${DOWNLOAD_PAGE}"
        echo ""
        echo "  2. 选择对应平台下载:"
        echo "     - Linux:   FutuOpenD_x.x.x_ubuntu20.04_x86_64.tar.gz"
        echo "     - macOS:   FutuOpenD_x.x.x_macos_x86_64.tar.gz"
        echo "     - Windows: FutuOpenD_x.x.x_windows_x64.zip"
        echo ""
        echo "  3. 解压到: ${FUTU_OPEND_DIR}"
        echo ""
        echo "  4. 运行: bash ${FUTU_HOME}/start_opend.sh"
        echo ""
        echo "  ============================================================"
    fi

    rm -rf "$TEMP_DIR"
}

# ============================================================
# 生成 FutuOpenD 配置文件
# ============================================================
configure_opend() {
    log_info "生成 FutuOpenD 配置..."

    FUTU_INI="${FUTU_CONFIG_DIR}/FutuOpenD.xml"

    # 确定交易环境
    if [ "$FUTU_TRADING_MODE" = "real" ]; then
        TRD_ENV="REAL"
        TRADE_PASSWORD_LEVEL="NONE"
    else
        TRD_ENV="SIMULATE"
        TRADE_PASSWORD_LEVEL="NONE"
    fi

    cat > "${FUTU_INI}" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!--
  BDE-Stock 自动生成 - FutuOpenD 配置文件
  生成时间: $(date)
  
  重要说明:
  - login_account / login_pwd 需填写富途牛牛账号
  - 首次登录需在手机/电脑上完成二次验证
  - 模拟交易使用虚拟资金，不会产生真实交易
-->
<config>
  <!-- 富途账号 -->
  <login_account>${FUTU_USERNAME:-your_account}</login_account>
  <login_pwd_md5>${FUTU_PASSWORD:-your_password_md5}</login_pwd_md5>
  
  <!-- 网络配置 -->
  <api_ip>127.0.0.1</api_ip>
  <api_port>${FUTU_PORT}</api_port>
  
  <!-- 交易环境: SIMULATE=模拟, REAL=实盘 -->
  <trd_env>${TRD_ENV}</trd_env>
  
  <!-- 交易密码等级 -->
  <trade_pwd_level>${TRADE_PASSWORD_LEVEL}</trade_pwd_level>
  
  <!-- 日志等级: NONE/ERROR/INFO/DEBUG/ALL -->
  <log_level>INFO</log_level>
  <log_dir>${FUTU_LOG_DIR}</log_dir>
  
  <!-- 订阅推送 -->
  <push_notify_type>0</push_notify_type>
  
  <!-- 订阅额度 -->
  <sub_quota_detail>1</sub_quota_detail>
  
  <!-- RSA 密钥对（可选，启用安全通信） -->
  <!-- <rsa_private_key></rsa_private_key> -->
  
  <!-- 协议类型: tcp / grpc -->
  <protocol_type>tcp</protocol_type>
  
  <!-- 是否启用双向认证 -->
  <enable_encrypt>false</enable_encrypt>
</config>
EOF

    log_info "配置文件: ${FUTU_INI}"
    log_warn "请编辑配置文件，填入真实的富途账号信息！"
}

# ============================================================
# 创建启动脚本
# ============================================================
create_start_script() {
    START_SCRIPT="${FUTU_HOME}/start_opend.sh"

    cat > "${START_SCRIPT}" << 'SCRIPT_EOF'
#!/bin/bash
# ============================================================
# FutuOpenD 启动脚本 - BDE-Stock
# ============================================================

FUTU_HOME="${HOME}/futu"
FUTU_OPEND_DIR="${FUTU_HOME}/opend"
FUTU_CONFIG_DIR="${FUTU_HOME}/config"
FUTU_LOG_DIR="${FUTU_HOME}/logs"
FUTU_PORT=11111

# 查找 FutuOpenD 可执行文件
OPEND_BIN=""
for f in "${FUTU_OPEND_DIR}"/*/FutuOpenD \
         "${FUTU_OPEND_DIR}"/*/FutuOpenD.exe \
         "${FUTU_OPEND_DIR}"/FutuOpenD \
         "${FUTU_OPEND_DIR}"/FutuOpenD.exe; do
    if [ -f "$f" ]; then
        OPEND_BIN="$f"
        break
    fi
done

if [ -z "$OPEND_BIN" ]; then
    echo "[ERROR] FutuOpenD 可执行文件未找到"
    echo "  请先安装 FutuOpenD 到: ${FUTU_OPEND_DIR}"
    echo "  下载: https://openapi.futunn.com/futu-api-doc/opend/opend-cmd.html"
    exit 1
fi

# 检查配置文件
CONFIG_FILE="${FUTU_CONFIG_DIR}/FutuOpenD.xml"
if [ ! -f "$CONFIG_FILE" ]; then
    echo "[ERROR] 配置文件不存在: $CONFIG_FILE"
    echo "  请先运行 deploy_futu_opend.sh 生成配置"
    exit 1
fi

echo "============================================================"
echo "  启动 FutuOpenD"
echo "  配置: ${CONFIG_FILE}"
echo "  端口: ${FUTU_PORT}"
echo "  日志: ${FUTU_LOG_DIR}"
echo "============================================================"

# 启动 FutuOpenD
chmod +x "$OPEND_BIN"
"$OPEND_BIN" -config="$CONFIG_FILE" 2>&1 | tee "${FUTU_LOG_DIR}/opend.log" &
OPEND_PID=$!

echo "[INFO] FutuOpenD PID: $OPEND_PID"
echo "[INFO] 等待启动..."

# 等待端口就绪
for i in $(seq 1 30); do
    if nc -z 127.0.0.1 $FUTU_PORT 2>/dev/null; then
        echo "[INFO] FutuOpenD 已就绪 (端口 ${FUTU_PORT})"
        echo "[INFO] BDE-Stock 可通过 futu-api 连接"
        exit 0
    fi
    sleep 1
done

echo "[WARN] FutuOpenD 可能在后台启动中，请稍后检查"
echo "  检查: nc -z 127.0.0.1 $FUTU_PORT"
echo "  日志: tail -f ${FUTU_LOG_DIR}/opend.log"
SCRIPT_EOF

    chmod +x "${START_SCRIPT}"
    log_info "启动脚本: ${START_SCRIPT}"
}

# ============================================================
# 验证安装
# ============================================================
verify_installation() {
    log_info "验证安装..."

    ERRORS=0

    # 检查 Python
    if command -v python3 &> /dev/null; then
        log_info "  Python: OK ($(python3 --version))"
    else
        log_error "  Python: 未找到"
        ERRORS=$((ERRORS + 1))
    fi

    # 检查 futu-api
    if python3 -c "import futu" 2>/dev/null; then
        log_info "  futu-api: OK"
    else
        log_warn "  futu-api: 未安装，运行: pip install futu-api"
    fi

    # 检查 FutuOpenD 配置
    if [ -f "${FUTU_CONFIG_DIR}/FutuOpenD.xml" ]; then
        log_info "  配置文件: OK"
    else
        log_warn "  配置文件: 未找到"
    fi

    # 检查 FutuOpenD 可执行文件
    FOUND_OPEND=false
    for f in "${FUTU_OPEND_DIR}"/*/FutuOpenD \
             "${FUTU_OPEND_DIR}"/FutuOpenD; do
        if [ -f "$f" ]; then
            FOUND_OPEND=true
            break
        fi
    done
    if $FOUND_OPEND; then
        log_info "  FutuOpenD: OK"
    else
        log_warn "  FutuOpenD: 未安装（需手动下载）"
    fi

    # 检查启动脚本
    if [ -x "${FUTU_HOME}/start_opend.sh" ]; then
        log_info "  启动脚本: OK"
    else
        log_warn "  启动脚本: 未找到"
    fi

    return $ERRORS
}

# ============================================================
# 创建 systemd 服务（仅 Linux）
# ============================================================
create_systemd_service() {
    if [[ "$OS_TYPE" != "debian" ]] && [[ "$OS_TYPE" != "redhat" ]]; then
        return
    fi

    log_info "创建 systemd 服务..."

    SERVICE_FILE="/etc/systemd/system/futu-opend.service"

    cat > /tmp/futu-opend.service << EOF
[Unit]
Description=FutuOpenD Gateway - BDE-Stock
After=network.target

[Service]
Type=simple
User=$(whoami)
ExecStart=$(cat /dev/null)
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal
Environment=FUTU_HOME=${FUTU_HOME}

[Install]
WantedBy=multi-user.target
EOF

    # 找到实际的启动命令
    OPEND_BIN=""
    for f in "${FUTU_OPEND_DIR}"/*/FutuOpenD "${FUTU_OPEND_DIR}"/FutuOpenD; do
        if [ -x "$f" ]; then
            OPEND_BIN="$f"
            break
        fi
    done

    if [ -n "$OPEND_BIN" ]; then
        sed -i "s|ExecStart=.*|ExecStart=${OPEND_BIN} -config=${FUTU_CONFIG_DIR}/FutuOpenD.xml|" /tmp/futu-opend.service
        sudo cp /tmp/futu-opend.service "$SERVICE_FILE"
        sudo systemctl daemon-reload
        log_info "systemd 服务已创建: futu-opend"
        log_warn "启动: sudo systemctl start futu-opend"
        log_warn "开机自启: sudo systemctl enable futu-opend"
    else
        log_warn "FutuOpenD 未安装，跳过 systemd 服务创建"
    fi

    rm -f /tmp/futu-opend.service
}

# ============================================================
# 快速测试脚本
# ============================================================
create_test_script() {
    TEST_SCRIPT="${FUTU_HOME}/test_connection.py"

    cat > "${TEST_SCRIPT}" << 'PYEOF'
#!/usr/bin/env python3
"""FutuOpenD 连接测试 - BDE-Stock"""

import sys
sys.path.insert(0, '/app/data/所有对话/主对话/BDE-Stock')

try:
    from futu_adapter import FutuAdapter
    adapter = FutuAdapter(host='127.0.0.1', port=11111, paper_trading=True)
    
    print("测试 FutuOpenD 连接...")
    if adapter.connect():
        print("[OK] 连接成功")
        
        acct = adapter.get_account()
        if acct:
            print(f"[OK] 账户: cash={acct.cash:.2f} pv={acct.portfolio_value:.2f}")
        else:
            print("[WARN] 无法获取账户信息")
        
        adapter.disconnect()
        print("[OK] 测试完成")
    else:
        print("[FAIL] 连接失败")
        print("请确认:")
        print("  1. FutuOpenD 已启动: bash ~/futu/start_opend.sh")
        print("  2. 端口 11111 可访问: nc -z 127.0.0.1 11111")
        sys.exit(1)
        
except ImportError as e:
    print(f"[FAIL] futu-api 未安装: {e}")
    print("请运行: pip install futu-api")
    sys.exit(1)
except Exception as e:
    print(f"[FAIL] 异常: {e}")
    sys.exit(1)
PYEOF

    log_info "测试脚本: ${TEST_SCRIPT}"
}

# ============================================================
# 主流程
# ============================================================
main() {
    print_banner

    detect_os

    echo "============================================================"
    echo "  交易模式: ${FUTU_TRADING_MODE} (simulate=模拟 / real=实盘)"
    echo "  目标端口: ${FUTU_PORT}"
    echo "  安装目录: ${FUTU_HOME}"
    echo "  支持市场: 美股(US) / 港股(HK) / A股(SH/SZ)"
    echo "============================================================"
    echo ""

    # 步骤1: 安装系统依赖
    install_dependencies

    # 步骤2: 安装 Python futu-api
    install_futu_api

    # 步骤3: 下载 FutuOpenD
    install_futu_opend

    # 步骤4: 生成配置
    configure_opend

    # 步骤5: 创建启动脚本
    create_start_script

    # 步骤6: 创建测试脚本
    create_test_script

    # 步骤7: 创建 systemd 服务（仅 Linux）
    create_systemd_service

    # 步骤8: 验证
    echo ""
    verify_installation

    echo ""
    echo "============================================================"
    echo "  安装完成！"
    echo ""
    echo "  后续步骤:"
    echo "    1. 编辑配置: vi ${FUTU_CONFIG_DIR}/FutuOpenD.xml"
    echo "       (填入富途账号信息)"
    echo "    2. 启动 OpenD: bash ${FUTU_HOME}/start_opend.sh"
    echo "    3. 测试连接:  python3 ${FUTU_HOME}/test_connection.py"
    echo "    4. 配置 BDE:   export BDE_BROKER=futu"
    echo "    5. 运行系统:   cd BDE-Stock && python test_connection.py --futu"
    echo ""
    echo "  FutuOpenD 端口: 127.0.0.1:${FUTU_PORT}"
    echo ""
    echo "  切换券商:"
    echo "    IBKR:  export BDE_BROKER=ibkr"
    echo "    Alpaca: export BDE_BROKER=alpaca"
    echo "    Futu:  export BDE_BROKER=futu"
    echo "============================================================"
}

# 执行
main "$@"
