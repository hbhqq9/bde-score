#!/bin/bash
# ============================================================
# BDE-Stock - IB Gateway 安装部署脚本
# 
# 安装 Interactive Brokers Gateway
# 用于 BDE-Stock 系统通过 ib_insync 连接 IBKR
#
# 支持平台: Linux (Ubuntu/Debian, CentOS/RHEL), macOS
# 使用 IBC 自动化 IB Gateway 启动和登录
# ============================================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 配置
IB_GATEWAY_VERSION="10.29"
IBC_VERSION="3.20.0"
IB_HOME="${HOME}/ibc"
IB_GATEWAY_DIR="${IB_HOME}/Jts"
IBC_DIR="${IB_HOME}/ibc"
LOG_DIR="${IB_HOME}/logs"

# IB Gateway 账户信息（通过环境变量传入，不硬编码）
IB_USERNAME="${IB_USERNAME:-}"
IB_PASSWORD="${IB_PASSWORD:-}"
IB_TRADING_MODE="${IB_TRADING_MODE:-paper}"  # paper | live

# 端口配置
PAPER_PORT=7497
LIVE_PORT=7496

print_banner() {
    echo ""
    echo "============================================================"
    echo "  BDE-Stock IB Gateway 部署工具"
    echo "  Interactive Brokers Gateway 安装与配置"
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
    else
        OS_TYPE="unknown"
    fi
    log_info "检测到操作系统: $OS_TYPE ($OSTYPE)"
}

# ============================================================
# 安装依赖
# ============================================================
install_dependencies() {
    log_info "安装依赖..."

    case "$OS_TYPE" in
        debian)
            sudo apt-get update -qq
            sudo apt-get install -y -qq \
                openjdk-17-jre-headless \
                xauth \
                xvfb \
                wget \
                unzip \
                libxrender1 \
                libxtst6 \
                libxi6
            ;;
        redhat)
            sudo yum install -y -q \
                java-17-openjdk-headless \
                xorg-x11-server-Xvfb \
                xorg-x11-xauth \
                wget \
                unzip
            ;;
        macos)
            if ! command -v brew &> /dev/null; then
                log_error "请先安装 Homebrew: https://brew.sh"
                exit 1
            fi
            brew install --cask temurin@17 2>/dev/null || true
            brew install wget 2>/dev/null || true
            ;;
        *)
            log_error "不支持的操作系统: $OS_TYPE"
            exit 1
            ;;
    esac

    log_info "Java 版本:"
    java -version 2>&1 || log_error "Java 未正确安装"
}

# ============================================================
# 下载并安装 IB Gateway
# ============================================================
install_ib_gateway() {
    log_info "安装 IB Gateway ${IB_GATEWAY_VERSION}..."

    mkdir -p "${IB_GATEWAY_DIR}" "${LOG_DIR}"

    # 下载链接
    IB_DOWNLOAD_URL="https://download2.interactivebrokers.com/installers/ibgateway/stable-standalone/ibgateway-stable-standalone-linux-x64-${IB_GATEWAY_VERSION}-standalone.zip"

    # macOS 使用不同链接
    if [[ "$OS_TYPE" == "macos" ]]; then
        IB_DOWNLOAD_URL="https://download2.interactivebrokers.com/installers/ibgateway/stable-standalone/ibgateway-stable-standalone-macosx-x64-${IB_GATEWAY_VERSION}-standalone.zip"
    fi

    TEMP_DIR=$(mktemp -d)
    ZIP_FILE="${TEMP_DIR}/ibgateway.zip"

    log_info "下载 IB Gateway..."
    if wget -q --show-progress -O "$ZIP_FILE" "$IB_DOWNLOAD_URL" 2>/dev/null; then
        log_info "解压安装..."
        unzip -q -o "$ZIP_FILE" -d "${IB_GATEWAY_DIR}"
        log_info "IB Gateway 安装完成: ${IB_GATEWAY_DIR}"
    else
        log_warn "自动下载失败，请手动下载:"
        log_warn "  1. 访问 https://www.interactivebrokers.com/en/trading/ibgateway-stable.php"
        log_warn "  2. 下载 Standalone 版本"
        log_warn "  3. 解压到 ${IB_GATEWAY_DIR}"
    fi

    rm -rf "$TEMP_DIR"
}

# ============================================================
# 下载并安装 IBC (IB Controller)
# ============================================================
install_ibc() {
    log_info "安装 IBC ${IBC_VERSION} (自动化控制器)..."

    mkdir -p "${IBC_DIR}"

    IBC_URL="https://github.com/IbcAlpha/IBC/releases/download/${IBC_VERSION}/ibc-${IBC_VERSION}.zip"

    TEMP_DIR=$(mktemp -d)
    ZIP_FILE="${TEMP_DIR}/ibc.zip"

    log_info "下载 IBC..."
    if wget -q --show-progress -O "$ZIP_FILE" "$IBC_URL" 2>/dev/null; then
        log_info "解压 IBC..."
        unzip -q -o "$ZIP_FILE" -d "${IBC_DIR}"
        chmod +x "${IBC_DIR}"/*.sh "${IBC_DIR}"/*.bat 2>/dev/null || true
        log_info "IBC 安装完成: ${IBC_DIR}"
    else
        log_warn "IBC 自动下载失败，请手动下载:"
        log_warn "  https://github.com/IbcAlpha/IBC/releases"
    fi

    rm -rf "$TEMP_DIR"
}

# ============================================================
# 配置 IBC
# ============================================================
configure_ibc() {
    log_info "配置 IBC..."

    IBC_INI="${IBC_DIR}/config.ini"

    cat > "${IBC_INI}" << EOF
# IBC 配置文件 - BDE-Stock 自动生成
# 生成时间: $(date)

LogToConsole=yes
FIX=no

# 交易模式
IbAutoClosedown=no

# 自动接受传入连接（供 ib_insync Socket 连接）
AllowBlindTrading=yes

# 不显示登录对话框（自动登录）
OverrideTwsApiPort=$( [ "$IB_TRADING_MODE" = "live" ] && echo "$LIVE_PORT" || echo "$PAPER_PORT" )

# 存储路径
IbDir=${IB_GATEWAY_DIR}

# 日志
LogsPath=${LOG_DIR}

# 诊断
DiagLog=yes
EOF

    log_info "IBC 配置完成: ${IBC_INI}"
}

# ============================================================
# 创建启动脚本
# ============================================================
create_start_script() {
    START_SCRIPT="${IB_HOME}/start_ib_gateway.sh"

    if [ "$IB_TRADING_MODE" = "live" ]; then
        PORT=$LIVE_PORT
        MODE="Live"
    else
        PORT=$PAPER_PORT
        MODE="Paper"
    fi

    cat > "${START_SCRIPT}" << 'SCRIPT_EOF'
#!/bin/bash
# IB Gateway 启动脚本 - BDE-Stock
# 使用 Xvfb 虚拟显示运行 IB Gateway

IB_HOME="${HOME}/ibc"
IBC_DIR="${IB_HOME}/ibc"
IB_GATEWAY_DIR="${IB_HOME}/Jts"
LOG_DIR="${IB_HOME}/logs"

# 配置
IB_GATEWAY_VERSION="10.29"
TRADING_MODE="PAPER"  # PAPER 或 LIVE

# 设置虚拟显示
export DISPLAY=:1

# 启动 Xvfb（如果未运行）
if ! pgrep -x "Xvfb" > /dev/null; then
    Xvfb :1 -screen 0 1024x768x24 &
    sleep 2
    echo "[INFO] Xvfb 已启动"
fi

# 设置 Java 内存
export JAVA_MEM="-Xmx512m"

# 启动 IB Gateway + IBC
echo "[INFO] 启动 IB Gateway (${TRADING_MODE})..."
echo "[INFO] Socket 端口: $( [ "$TRADING_MODE" = "LIVE" ] && echo "7496" || echo "7497" )"

"${IBC_DIR}/gatewaystart.sh" \
    --ibc-path="${IBC_DIR}" \
    --ibc-ini="${IBC_DIR}/config.ini" \
    --mode="${TRADING_MODE}" \
    --ibc-log-dir="${LOG_DIR}" \
    --user-password-dir="${IB_HOME}/credentials" 2>&1 | tee "${LOG_DIR}/ibgateway.log"
SCRIPT_EOF

    chmod +x "${START_SCRIPT}"
    log_info "启动脚本: ${START_SCRIPT}"
}

# ============================================================
# 配置环境变量
# ============================================================
setup_credentials() {
    CRED_DIR="${IB_HOME}/credentials"
    mkdir -p "${CRED_DIR}"

    if [ -n "$IB_USERNAME" ] && [ -n "$IB_PASSWORD" ]; then
        # 创建凭证文件
        cat > "${CRED_DIR}/ib_credentials.txt" << EOF
${IB_USERNAME}
${IB_PASSWORD}
EOF
        chmod 600 "${CRED_DIR}/ib_credentials.txt"
        log_info "凭证文件已创建: ${CRED_DIR}/ib_credentials.txt"
    else
        log_warn "未提供 IB 账户信息"
        log_warn "请设置环境变量后重新运行:"
        log_warn "  export IB_USERNAME='your_username'"
        log_warn "  export IB_PASSWORD='your_password'"
        log_warn "  bash deploy_ib_gateway.sh"
    fi
}

# ============================================================
# 验证安装
# ============================================================
verify_installation() {
    log_info "验证安装..."

    ERRORS=0

    # 检查 Java
    if command -v java &> /dev/null; then
        log_info "  Java: OK ($(java -version 2>&1 | head -1))"
    else
        log_error "  Java: 未找到"
        ERRORS=$((ERRORS + 1))
    fi

    # 检查 Xvfb
    if command -v Xvfb &> /dev/null; then
        log_info "  Xvfb: OK"
    else
        log_warn "  Xvfb: 未找到 (macOS 不需要)"
    fi

    # 检查 Python ib_insync
    if python3 -c "import ib_insync" 2>/dev/null; then
        log_info "  ib_insync: OK"
    else
        log_warn "  ib_insync: 未安装，运行: pip install ib_insync"
    fi

    # 检查 IB Gateway
    if [ -d "${IB_GATEWAY_DIR}" ] && [ "$(ls -A ${IB_GATEWAY_DIR} 2>/dev/null)" ]; then
        log_info "  IB Gateway: OK (${IB_GATEWAY_DIR})"
    else
        log_warn "  IB Gateway: 未安装或为空"
    fi

    # 检查 IBC
    if [ -d "${IBC_DIR}" ] && [ -f "${IBC_DIR}/gatewaystart.sh" ]; then
        log_info "  IBC: OK (${IBC_DIR})"
    else
        log_warn "  IBC: 未安装"
    fi

    return $ERRORS
}

# ============================================================
# 主流程
# ============================================================
main() {
    print_banner

    detect_os

    echo "============================================================"
    echo "  安装模式: ${IB_TRADING_MODE}"
    echo "  目标端口: $([ "$IB_TRADING_MODE" = "live" ] && echo "$LIVE_PORT (Live)" || echo "$PAPER_PORT (Paper)")"
    echo "  安装目录: ${IB_HOME}"
    echo "============================================================"
    echo ""

    # 步骤1: 安装依赖
    install_dependencies

    # 步骤2: 安装 IB Gateway
    install_ib_gateway

    # 步骤3: 安装 IBC
    install_ibc

    # 步骤4: 配置
    configure_ibc

    # 步骤5: 创建启动脚本
    create_start_script

    # 步骤6: 设置凭证
    setup_credentials

    # 步骤7: 验证
    echo ""
    verify_installation

    echo ""
    echo "============================================================"
    echo "  安装完成！"
    echo ""
    echo "  后续步骤:"
    echo "    1. 设置 IB 账户: export IB_USERNAME='xxx' IB_PASSWORD='xxx'"
    echo "    2. 启动 IB Gateway: bash ${IB_HOME}/start_ib_gateway.sh"
    echo "    3. 测试连接: cd /path/to/BDE-Stock && python test_connection.py --ibkr"
    echo ""
    echo "  BDE-Stock 将通过 ib_insync Socket 连接:"
    echo "    Paper: 127.0.0.1:7497"
    echo "    Live:  127.0.0.1:7496"
    echo "============================================================"
}

# 执行
main "$@"
