#!/bin/bash
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'


API_URL="${API_URL:-http://localhost:8000}"


print_header() {
    echo ""
    echo -e "${PURPLE}════════════════════════════════════════════════════════════${NC}"
    echo -e "${PURPLE}  $1${NC}"
    echo -e "${PURPLE}════════════════════════════════════════════════════════════${NC}"
}

print_step() {
    echo -e "${CYAN}▶ $1${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ $1${NC}"
}

api_post() {
    local endpoint=$1
    local data=$2
    local response
    local http_code
    
    response=$(curl -s -w "\n%{http_code}" -X POST "${API_URL}${endpoint}" \
        -H "Content-Type: application/json" \
        -d "$data")
    
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')
    
    if [ "$http_code" -ge 400 ]; then
        echo "ERROR:$http_code:$body"
        return 1
    fi
    
    echo "$body"
    return 0
}

api_get() {
    local endpoint=$1
    curl -s -X GET "${API_URL}${endpoint}"
}

api_patch() {
    local endpoint=$1
    local data=$2
    curl -s -X PATCH "${API_URL}${endpoint}" \
        -H "Content-Type: application/json" \
        -d "$data"
}

extract_id() {
    local json=$1
    echo "$json" | python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))" 2>/dev/null || echo ""
}


print_header "🚀 Mini-CRM Demo Setup"

print_step "Проверка доступности API..."

MAX_RETRIES=10
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -s "${API_URL}/health" | grep -q "ok"; then
        print_success "API доступен: ${API_URL}"
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo -e "${YELLOW}  Ожидание сервера... ($RETRY_COUNT/$MAX_RETRIES)${NC}"
    sleep 1
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    print_error "API недоступен. Запустите сервер: uvicorn app.main:app --reload"
    exit 1
fi

sleep 1

print_header "👥 Создание операторов"

print_step "Создаём оператора: Алексей Смирнов (лимит: 5)"
OP1=$(api_post "/operators" '{"name": "Алексей Смирнов", "is_active": true, "max_active_contacts": 5}')
if [[ "$OP1" == ERROR:* ]]; then
    print_error "Ошибка создания оператора: $OP1"
    exit 1
fi
OP1_ID=$(extract_id "$OP1")
print_success "Создан оператор ID=$OP1_ID"
sleep 0.2

print_step "Создаём оператора: Мария Иванова (лимит: 10)"
OP2=$(api_post "/operators" '{"name": "Мария Иванова", "is_active": true, "max_active_contacts": 10}')
OP2_ID=$(extract_id "$OP2")
print_success "Создан оператор ID=$OP2_ID"
sleep 0.2

print_step "Создаём оператора: Дмитрий Козлов (лимит: 8)"
OP3=$(api_post "/operators" '{"name": "Дмитрий Козлов", "is_active": true, "max_active_contacts": 8}')
OP3_ID=$(extract_id "$OP3")
print_success "Создан оператор ID=$OP3_ID"
sleep 0.2

print_step "Создаём оператора: Елена Петрова (неактивен)"
OP4=$(api_post "/operators" '{"name": "Елена Петрова", "is_active": false, "max_active_contacts": 5}')
OP4_ID=$(extract_id "$OP4")
print_success "Создан оператор ID=$OP4_ID (неактивен - для демонстрации)"
sleep 0.2

if [ -z "$OP1_ID" ] || [ -z "$OP2_ID" ] || [ -z "$OP3_ID" ]; then
    print_error "Не удалось получить ID операторов"
    echo "OP1: $OP1"
    echo "OP2: $OP2"
    echo "OP3: $OP3"
    exit 1
fi

print_header "🤖 Создание источников (ботов)"

print_step "Создаём источник: Telegram Bot (основной)"
SRC1=$(api_post "/sources" '{"name": "Telegram Bot", "code": "telegram_main", "description": "Основной Telegram бот для продаж", "is_active": true}')
if [[ "$SRC1" == ERROR:* ]]; then
    print_error "Ошибка создания источника: $SRC1"
    exit 1
fi
SRC1_ID=$(extract_id "$SRC1")
print_success "Создан источник ID=$SRC1_ID (code: telegram_main)"
sleep 0.2

print_step "Создаём источник: WhatsApp Bot"
SRC2=$(api_post "/sources" '{"name": "WhatsApp Bot", "code": "whatsapp", "description": "WhatsApp Business API", "is_active": true}')
SRC2_ID=$(extract_id "$SRC2")
print_success "Создан источник ID=$SRC2_ID (code: whatsapp)"
sleep 0.2

print_step "Создаём источник: Виджет на сайте"
SRC3=$(api_post "/sources" '{"name": "Website Widget", "code": "web_widget", "description": "Чат-виджет на сайте company.ru", "is_active": true}')
SRC3_ID=$(extract_id "$SRC3")
print_success "Создан источник ID=$SRC3_ID (code: web_widget)"
sleep 0.2

print_step "Создаём источник: VK Bot"
SRC4=$(api_post "/sources" '{"name": "VK Bot", "code": "vk_bot", "description": "Бот в сообществе ВКонтакте", "is_active": true}')
SRC4_ID=$(extract_id "$SRC4")
print_success "Создан источник ID=$SRC4_ID (code: vk_bot)"
sleep 0.2

if [ -z "$SRC1_ID" ] || [ -z "$SRC2_ID" ] || [ -z "$SRC3_ID" ] || [ -z "$SRC4_ID" ]; then
    print_error "Не удалось получить ID источников"
    exit 1
fi

print_header "⚖️  Настройка распределения трафика"

print_info "Telegram Bot: Алексей(10), Мария(30), Дмитрий(20) → 17%, 50%, 33%"

api_post "/assignments" "{\"operator_id\": $OP1_ID, \"source_id\": $SRC1_ID, \"weight\": 10}" > /dev/null
print_step "  Алексей → Telegram (вес: 10)"
sleep 0.1

api_post "/assignments" "{\"operator_id\": $OP2_ID, \"source_id\": $SRC1_ID, \"weight\": 30}" > /dev/null
print_step "  Мария → Telegram (вес: 30)"
sleep 0.1

api_post "/assignments" "{\"operator_id\": $OP3_ID, \"source_id\": $SRC1_ID, \"weight\": 20}" > /dev/null
print_step "  Дмитрий → Telegram (вес: 20)"
sleep 0.1

print_success "Настроено распределение для Telegram"

echo ""
print_info "WhatsApp: Мария(50), Дмитрий(50) → 50%, 50%"

api_post "/assignments" "{\"operator_id\": $OP2_ID, \"source_id\": $SRC2_ID, \"weight\": 50}" > /dev/null
print_step "  Мария → WhatsApp (вес: 50)"
sleep 0.1

api_post "/assignments" "{\"operator_id\": $OP3_ID, \"source_id\": $SRC2_ID, \"weight\": 50}" > /dev/null
print_step "  Дмитрий → WhatsApp (вес: 50)"
sleep 0.1

print_success "Настроено распределение для WhatsApp"

echo ""
print_info "Website Widget: Алексей(100) → 100%"

api_post "/assignments" "{\"operator_id\": $OP1_ID, \"source_id\": $SRC3_ID, \"weight\": 100}" > /dev/null
print_step "  Алексей → Website (вес: 100)"
sleep 0.1

print_success "Настроено распределение для Website Widget"

echo ""
print_info "VK Bot: Дмитрий(70), Алексей(30) → 70%, 30%"

api_post "/assignments" "{\"operator_id\": $OP3_ID, \"source_id\": $SRC4_ID, \"weight\": 70}" > /dev/null
print_step "  Дмитрий → VK (вес: 70)"
sleep 0.1

api_post "/assignments" "{\"operator_id\": $OP1_ID, \"source_id\": $SRC4_ID, \"weight\": 30}" > /dev/null
print_step "  Алексей → VK (вес: 30)"
sleep 0.1

print_success "Настроено распределение для VK Bot"



print_header "📨 Создание тестовых обращений"

print_info "Создаём 15 обращений из разных источников..."
echo ""

create_contact() {
    local external_id=$1
    local source_code=$2
    local message=$3
    local name=$4
    local phone=$5
    
    local response=$(api_post "/contacts" "{
        \"lead_external_id\": \"$external_id\",
        \"source_code\": \"$source_code\",
        \"message\": \"$message\",
        \"lead_name\": \"$name\",
        \"lead_phone\": \"$phone\"
    }")
    
    if [[ "$response" == ERROR:* ]]; then
        echo -e "  ${YELLOW}⚠ $name ($source_code) → ОШИБКА${NC}"
        return
    fi
    
    local operator_name=$(echo "$response" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('operator_name') or 'Не назначен')" 2>/dev/null || echo "?")
    
    if [ "$operator_name" = "Не назначен" ] || [ "$operator_name" = "null" ] || [ -z "$operator_name" ]; then
        echo -e "  ${YELLOW}⚠ $name ($source_code) → БЕЗ ОПЕРАТОРА${NC}"
    else
        echo -e "  ${GREEN}✓${NC} $name ($source_code) → ${CYAN}$operator_name${NC}"
    fi
    
    sleep 0.1
}

print_step "Обращения из Telegram:"
create_contact "tg_user_101" "telegram_main" "Здравствуйте! Интересует ваш продукт" "Иван Петров" "+79001234501"
create_contact "tg_user_102" "telegram_main" "Хочу узнать цены" "Анна Сидорова" "+79001234502"
create_contact "tg_user_103" "telegram_main" "Нужна консультация" "Пётр Николаев" "+79001234503"
create_contact "tg_user_104" "telegram_main" "Как оформить заказ?" "Ольга Фёдорова" "+79001234504"
create_contact "tg_user_105" "telegram_main" "Есть ли скидки?" "Сергей Михайлов" "+79001234505"

echo ""
print_step "Обращения из WhatsApp:"
create_contact "wa_user_201" "whatsapp" "Добрый день, нужна помощь" "Екатерина Волкова" "+79001234601"
create_contact "wa_user_202" "whatsapp" "Вопрос по доставке" "Андрей Соколов" "+79001234602"
create_contact "wa_user_203" "whatsapp" "Хочу оформить возврат" "Наталья Козлова" "+79001234603"

echo ""
print_step "Обращения с сайта:"
create_contact "web_user_301" "web_widget" "Не работает личный кабинет" "Максим Лебедев" "+79001234701"
create_contact "web_user_302" "web_widget" "Как изменить заказ?" "Виктория Новикова" "+79001234702"

echo ""
print_step "Обращения из VK:"
create_contact "vk_user_401" "vk_bot" "Привет! Есть вопрос" "Артём Морозов" "+79001234801"
create_contact "vk_user_402" "vk_bot" "Какие способы оплаты?" "Дарья Павлова" "+79001234802"

echo ""
print_step "Повторные обращения (тот же лид, другой источник):"
create_contact "tg_user_101" "whatsapp" "Это снова я, теперь из WhatsApp" "Иван Петров" "+79001234501"
create_contact "wa_user_201" "telegram_main" "Пишу из Telegram тоже" "Екатерина Волкова" "+79001234601"
create_contact "web_user_301" "vk_bot" "Дублирую вопрос в VK" "Максим Лебедев" "+79001234701"

print_success "Создано 15 обращений"


print_header "✅ Закрытие некоторых обращений"

print_step "Закрываем обращение ID=1 (освобождаем нагрузку оператора)"
api_patch "/contacts/1/status" '{"status": "closed"}' > /dev/null 2>&1
print_success "Обращение #1 закрыто"

print_step "Переводим обращение ID=2 в статус 'in_progress'"
api_patch "/contacts/2/status" '{"status": "in_progress"}' > /dev/null 2>&1
print_success "Обращение #2 в работе"


print_header "📊 Статистика системы"

echo ""
print_step "Общая статистика:"
STATS=$(api_get "/stats")
echo "$STATS" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(f\"  Операторов: {data['total_operators']} (активных: {data['active_operators']})\")
    print(f\"  Источников: {data['total_sources']}\")
    print(f\"  Лидов: {data['total_leads']}\")
    print(f\"  Обращений: {data['total_contacts']} (активных: {data['active_contacts']})\")
except Exception as e:
    print(f'  Ошибка парсинга: {e}')
"

echo ""
print_step "Нагрузка операторов:"
OPERATORS=$(api_get "/operators")
echo "$OPERATORS" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if not data:
        print('  Нет операторов')
    else:
        for op in data:
            status = '🟢' if op['is_active'] else '🔴'
            load = op['current_load']
            max_load = op['max_active_contacts']
            bar_len = 20
            filled = int(load / max_load * bar_len) if max_load > 0 else 0
            bar = '█' * filled + '░' * (bar_len - filled)
            print(f\"  {status} {op['name']}: [{bar}] {load}/{max_load}\")
except Exception as e:
    print(f'  Ошибка: {e}')
"

echo ""
print_step "Распределение по источникам:"
SOURCES=$(api_get "/sources")
echo "$SOURCES" | python3 -c "
import sys, json, urllib.request

API_URL = 'http://localhost:8000'

try:
    sources = json.load(sys.stdin)
    for src in sources:
        src_id = src['id']
        # Получаем детали источника
        with urllib.request.urlopen(f'{API_URL}/sources/{src_id}') as resp:
            data = json.loads(resp.read().decode())
            print(f\"  📌 {data['name']} ({data['code']}):\")
            if data.get('operators'):
                for op in data['operators']:
                    print(f\"      - {op['operator_name']}: вес {op['weight']}, нагрузка {op['current_load']}/{op['max_active_contacts']}\")
            else:
                print('      (нет операторов)')
except Exception as e:
    print(f'  Ошибка: {e}')
"

print_header "👤 Пример: лид с обращениями из разных источников"

print_step "Лид 'Иван Петров' (tg_user_101) обращался из Telegram и WhatsApp:"
LEADS=$(api_get "/leads")
echo "$LEADS" | python3 -c "
import sys, json, urllib.request

API_URL = 'http://localhost:8000'

try:
    leads = json.load(sys.stdin)
    # Находим лида Иван Петров
    ivan = None
    for lead in leads:
        if 'tg_user_101' in lead.get('external_id', ''):
            ivan = lead
            break
    
    if ivan:
        lead_id = ivan['id']
        with urllib.request.urlopen(f'{API_URL}/leads/{lead_id}') as resp:
            data = json.loads(resp.read().decode())
            print(f\"  External ID: {data['external_id']}\")
            print(f\"  Имя: {data.get('name', 'Не указано')}\")
            print(f\"  Телефон: {data.get('phone', 'Не указан')}\")
            print(f\"  Обращений: {len(data.get('contacts', []))}\")
            print()
            for c in data.get('contacts', []):
                status_icon = {'new': '🆕', 'in_progress': '🔄', 'closed': '✅'}.get(c['status'], '❓')
                op = c.get('operator_name') or 'Не назначен'
                print(f\"    {status_icon} #{c['id']}: {c['source_code']} → {op} ({c['status']})\")
    else:
        print('  Лид не найден')
except Exception as e:
    print(f'  Ошибка: {e}')
"

print_header "🎉 Демо-данные успешно созданы!"

echo ""
echo -e 