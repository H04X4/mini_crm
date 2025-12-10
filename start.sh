#!/bin/bash
set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}╔═══════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║     Mini-CRM: Lead Distribution Demo                  ║${NC}"
echo -e "${CYAN}╚═══════════════════════════════════════════════════════╝${NC}"
echo ""


rm -f mini_crm.db
echo -e "${GREEN}Запускаем сервер...${NC}"
uvicorn app.main:app --host 0.0.0.0 --port 8000 &
SERVER_PID=$!

echo -e "${YELLOW}Ожидаем готовности сервера...${NC}"
sleep 3

if ! curl -s http://localhost:8000/health > /dev/null; then
    echo "Сервер не запустился!"
    kill $SERVER_PID 2>/dev/null
    exit 1
fi

echo -e "${GREEN}Сервер запущен (PID: $SERVER_PID)${NC}"
echo ""


bash setup_demo.sh

echo ""
echo -e "${CYAN}═══════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}Сервер работает на http://localhost:8000${NC}"
echo -e "${GREEN}Swagger UI: http://localhost:8000/docs${NC}"
echo -e "${YELLOW}Для остановки: kill $SERVER_PID${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════════${NC}"

trap "echo ''; echo 'Останавливаем сервер...'; kill $SERVER_PID 2>/dev/null; exit 0" SIGINT SIGTERM
wait $SERVER_PID