#!/bin/bash

# 配置
function discover_base_url() {
    local host="127.0.0.1"
    local start_port=8000
    local max_attempts=100
    local port=$start_port
    for ((i=0; i<=max_attempts; i++)); do
        local url="http://${host}:${port}"
        if curl -s --max-time 1 "${url}/docs" > /dev/null; then
            echo "$url"
            return 0
        fi
        port=$((start_port + i + 1))
    done
    return 1
}

BASE_URL=${BASE_URL:-"$(discover_base_url)"}
if [ -z "$BASE_URL" ]; then
    BASE_URL="http://127.0.0.1:8000"
fi
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查服务是否运行
if ! curl -s "$BASE_URL/docs" > /dev/null; then
    echo -e "${RED}Error: Service is not running at $BASE_URL${NC}"
    echo "Please run 'python main.py' in a separate terminal."
    exit 1
fi

echo -e "${GREEN}=== Starting Acceptance Test Suite ===${NC}\n"

# 指标收集
TOTAL=0
PASSED=0
FAILED=0
START_TS=$(date +%s%3N)

# ==============================================================================
# 工具函数
# ==============================================================================

function run_test() {
    local test_name="$1"
    local method="$2"
    local endpoint="$3"
    local body="$4"
    local expected_code="$5"

    echo -e "${YELLOW}[TEST] $test_name${NC}"
    echo -e "Request: $method $endpoint"
    local t0=$(date +%s%3N)
    
    if [ ! -z "$body" ]; then
        echo "Body: $body"
        response=$(curl -s -w "\n%{http_code}" -X "$method" "$BASE_URL$endpoint" \
            -H "Content-Type: application/json" \
            -d "$body")
    else
        response=$(curl -s -w "\n%{http_code}" -X "$method" "$BASE_URL$endpoint" \
            -H "Content-Type: application/json")
    fi

    # 分离响应体和状态码
    http_code=$(echo "$response" | tail -n1)
    response_body=$(echo "$response" | sed '$d')

    # 格式化 JSON 输出 (如果安装了 python)
    formatted_body=$(echo "$response_body" | python3 -m json.tool 2>/dev/null || echo "$response_body")

    echo -e "Response Code: $http_code"
    echo -e "Response Body:\n$formatted_body"
    local t1=$(date +%s%3N)
    local latency=$((t1 - t0))
    TOTAL=$((TOTAL + 1))

    if [ "$http_code" -eq "$expected_code" ]; then
        PASSED=$((PASSED + 1))
        echo -e "${GREEN}[PASS]${NC} (latency=${latency}ms)\n"
    else
        FAILED=$((FAILED + 1))
        echo -e "${RED}[FAIL] Expected $expected_code but got $http_code${NC} (latency=${latency}ms)\n"
        exit 1
    fi
}

# ==============================================================================
# 1. 创建 Prompt (正常流程)
# ==============================================================================
run_test "Create Prompt (Happy Path)" \
    "POST" \
    "/prompts" \
    '{
        "name": "acceptance_test_prompt",
        "description": "A prompt for acceptance testing",
        "roles": [
            {"role_type": "system", "content": "You are a test bot", "order": 1},
            {"role_type": "user", "content": "Hello {name}", "order": 2}
        ],
        "tags": ["test", "acceptance"],
        "llm_config": {
            "model": "gpt-3.5-turbo",
            "temperature": 0.7
        }
    }' \
    200

# ==============================================================================
# 2. 创建 Prompt (异常流程 - 名字无效)
# ==============================================================================
# 测试 Pydantic 校验：名字包含空格应被拒绝
run_test "Create Prompt (Invalid Name - 422)" \
    "POST" \
    "/prompts" \
    '{
        "name": "invalid name with spaces",
        "description": "Should fail",
        "roles": [{"role_type": "user", "content": "hi", "order": 1}]
    }' \
    422

# ==============================================================================
# 3. 获取 Prompt (正常流程)
# ==============================================================================
run_test "Get Prompt (Happy Path)" \
    "POST" \
    "/prompts/get" \
    '{
        "name": "acceptance_test_prompt",
        "output_format": "openai",
        "template_vars": {"name": "Developer"}
    }' \
    200

# ==============================================================================
# 4. 获取 Prompt (异常流程 - 不存在)
# ==============================================================================
run_test "Get Prompt (Not Found - 404)" \
    "POST" \
    "/prompts/get" \
    '{
        "name": "non_existent_prompt_12345"
    }' \
    404

# ==============================================================================
# 5. 搜索 Prompt (正常流程)
# ==============================================================================
run_test "Search Prompt (By Tag)" \
    "POST" \
    "/prompts/search" \
    '{
        "tags": ["acceptance"],
        "limit": 5
    }' \
    200

# 5.1 基于 embedding 的搜索（构造查询）
run_test "Search Prompt (By Query Embedding)" \
    "POST" \
    "/prompts/search" \
    '{
        "query": "acceptance testing",
        "limit": 5
    }' \
    200

# ==============================================================================
# 6. 更新 Prompt (正常流程 - 创建新版本)
# ==============================================================================
# 修正点：Body 中添加了 "name" 字段以通过 Pydantic 校验
# 注意：version_number=1 是当前版本，更新后应生成 v1.1
run_test "Update Prompt (Create v1.1)" \
    "PUT" \
    "/prompts/acceptance_test_prompt?version_number=1" \
    '{
        "name": "acceptance_test_prompt",
        "description": "Updated description for v1.1",
        "roles": [
            {"role_type": "system", "content": "You are an updated bot", "order": 1},
            {"role_type": "user", "content": "Hello {name}", "order": 2}
        ],
        "version_type": "minor"
    }' \
    200

# ==============================================================================
# 7. 激活旧版本 (正常流程)
# ==============================================================================
# 激活 v1.0 并设为 latest
run_test "Activate Version 1.0" \
    "POST" \
    "/prompts/acceptance_test_prompt/versions/1.0/activate?set_as_latest=true" \
    "" \
    200

# ==============================================================================
# 8. 删除 Prompt (正常流程)
# ==============================================================================
run_test "Delete Prompt" \
    "DELETE" \
    "/prompts/acceptance_test_prompt" \
    "" \
    200

# ==============================================================================
# 9. 删除 Prompt (异常流程 - 规则校验，应为400)
# ==============================================================================
run_test "Delete Prompt (Min Active Rule - 400)" \
    "DELETE" \
    "/prompts/acceptance_test_prompt" \
    "" \
    400

# ==============================================================================
# 10. 删除 Prompt (异常流程 - 不存在，应为404)
# ==============================================================================
run_test "Delete Prompt (Not Found - 404)" \
    "DELETE" \
    "/prompts/non_existent_prompt_12345" \
    "" \
    404

echo -e "${GREEN}=== All Acceptance Tests Passed Successfully! ===${NC}"

# 汇总报告
END_TS=$(date +%s%3N)
DURATION=$((END_TS - START_TS))
SUCCESS_RATE=$(awk -v p=$PASSED -v t=$TOTAL 'BEGIN{printf "%.2f", (t>0)?(p*100.0/t):0}')
echo "{" > acceptance_report.json
echo "  \"total\": $TOTAL," >> acceptance_report.json
echo "  \"passed\": $PASSED," >> acceptance_report.json
echo "  \"failed\": $FAILED," >> acceptance_report.json
echo "  \"success_rate\": $SUCCESS_RATE," >> acceptance_report.json
echo "  \"duration_ms\": $DURATION," >> acceptance_report.json
echo "  \"base_url\": \"$BASE_URL\"" >> acceptance_report.json
echo "}" >> acceptance_report.json
echo -e "Report written to acceptance_report.json"
