#!/bin/bash

# Report Checker Pro - Start Script
# 一键启动前后端服务

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/frontend"

# Log directory
LOG_DIR="$SCRIPT_DIR/logs"
mkdir -p "$LOG_DIR"

# Function to print colored messages
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if a port is in use
check_port() {
    local port=$1
    if lsof -i :$port > /dev/null 2>&1; then
        return 0  # Port is in use
    else
        return 1  # Port is free
    fi
}

# Function to kill process on port
kill_port() {
    local port=$1
    if check_port $port; then
        print_warning "Port $port is in use, killing existing process..."
        lsof -ti :$port | xargs kill -9 2>/dev/null || true
        sleep 1
    fi
}

# Function to start backend
start_backend() {
    print_info "Starting backend server..."

    cd "$BACKEND_DIR"

    # Check if virtual environment exists
    if [ ! -d ".venv" ]; then
        print_error "Virtual environment not found. Please run: python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
        exit 1
    fi

    # Activate virtual environment and start server
    source .venv/bin/activate

    # Kill existing process on port 8000
    kill_port 8000

    # Start uvicorn in background
    nohup uvicorn app.main:app --host 127.0.0.1 --port 8000 > "$LOG_DIR/backend.log" 2>&1 &
    BACKEND_PID=$!
    echo $BACKEND_PID > "$LOG_DIR/backend.pid"

    # Wait for backend to start
    sleep 3

    # Check if backend is running
    if curl -s http://127.0.0.1:8000/api/health > /dev/null; then
        print_success "Backend server started on http://127.0.0.1:8000"
    else
        print_error "Backend server failed to start. Check logs at $LOG_DIR/backend.log"
        exit 1
    fi
}

# Function to start frontend
start_frontend() {
    print_info "Starting frontend server..."

    cd "$FRONTEND_DIR"

    # Check if node_modules exists
    if [ ! -d "node_modules" ]; then
        print_error "node_modules not found. Please run: npm install"
        exit 1
    fi

    # Kill existing process on port 5173
    kill_port 5173

    # Start vite in background
    nohup npm run dev -- --host 127.0.0.1 > "$LOG_DIR/frontend.log" 2>&1 &
    FRONTEND_PID=$!
    echo $FRONTEND_PID > "$LOG_DIR/frontend.pid"

    # Wait for frontend to start
    sleep 5

    # Check if frontend is running
    if check_port 5173; then
        print_success "Frontend server started on http://127.0.0.1:5173"
    else
        print_error "Frontend server failed to start. Check logs at $LOG_DIR/frontend.log"
        exit 1
    fi
}

# Function to stop all services
stop_services() {
    print_info "Stopping all services..."

    # Stop backend
    if [ -f "$LOG_DIR/backend.pid" ]; then
        kill $(cat "$LOG_DIR/backend.pid") 2>/dev/null || true
        rm "$LOG_DIR/backend.pid"
    fi
    kill_port 8000

    # Stop frontend
    if [ -f "$LOG_DIR/frontend.pid" ]; then
        kill $(cat "$LOG_DIR/frontend.pid") 2>/dev/null || true
        rm "$LOG_DIR/frontend.pid"
    fi
    kill_port 5173

    print_success "All services stopped"
}

# Function to show status
show_status() {
    echo ""
    echo "======================================"
    echo "  Report Checker Pro - Status"
    echo "======================================"
    echo ""

    if check_port 8000; then
        echo -e "Backend:  ${GREEN}Running${NC} (http://127.0.0.1:8000)"
    else
        echo -e "Backend:  ${RED}Stopped${NC}"
    fi

    if check_port 5173; then
        echo -e "Frontend: ${GREEN}Running${NC} (http://127.0.0.1:5173)"
    else
        echo -e "Frontend: ${RED}Stopped${NC}"
    fi

    echo ""
    echo "Log files:"
    echo "  - Backend:  $LOG_DIR/backend.log"
    echo "  - Frontend: $LOG_DIR/frontend.log"
    echo ""
}

# Main script
case "${1:-start}" in
    start)
        print_info "Starting Report Checker Pro..."
        start_backend
        start_frontend
        show_status
        print_success "All services started successfully!"
        print_info "Open http://127.0.0.1:5173 in your browser"
        ;;
    stop)
        stop_services
        ;;
    restart)
        stop_services
        sleep 2
        start_backend
        start_frontend
        show_status
        ;;
    status)
        show_status
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status}"
        exit 1
        ;;
esac
