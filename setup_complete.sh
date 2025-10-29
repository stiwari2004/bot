#!/bin/bash

# Troubleshooting AI - Complete Setup Script
echo "🔧 Troubleshooting AI - Complete System Setup"
echo "=============================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
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

# Check if Docker is running
check_docker() {
    print_status "Checking Docker status..."
    if ! docker info > /dev/null 2>&1; then
        print_error "Docker is not running. Please start Docker Desktop and try again."
        exit 1
    fi
    print_success "Docker is running"
}

# Check if required ports are available
check_ports() {
    print_status "Checking port availability..."
    
    if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1; then
        print_warning "Port 8000 is already in use. This might be our backend."
    else
        print_success "Port 8000 is available"
    fi
    
    if lsof -Pi :3000 -sTCP:LISTEN -t >/dev/null 2>&1; then
        print_warning "Port 3000 is already in use. This might be our frontend."
    else
        print_success "Port 3000 is available"
    fi
    
    if lsof -Pi :5432 -sTCP:LISTEN -t >/dev/null 2>&1; then
        print_warning "Port 5432 is already in use. This might be our database."
    else
        print_success "Port 5432 is available"
    fi
}

# Build and start all services
start_services() {
    print_status "Building and starting all services..."
    
    # Stop any existing containers
    print_status "Stopping existing containers..."
    docker compose down > /dev/null 2>&1
    
    # Build and start services
    print_status "Building Docker images..."
    if docker compose build; then
        print_success "Docker images built successfully"
    else
        print_error "Failed to build Docker images"
        exit 1
    fi
    
    print_status "Starting services..."
    if docker compose up -d; then
        print_success "Services started successfully"
    else
        print_error "Failed to start services"
        exit 1
    fi
}

# Wait for services to be ready
wait_for_services() {
    print_status "Waiting for services to be ready..."
    
    # Wait for backend
    print_status "Waiting for backend to be ready..."
    for i in {1..30}; do
        if curl -s http://localhost:8000/health > /dev/null 2>&1; then
            print_success "Backend is ready"
            break
        fi
        if [ $i -eq 30 ]; then
            print_error "Backend failed to start within 30 seconds"
            exit 1
        fi
        sleep 1
    done
    
    # Wait for frontend
    print_status "Waiting for frontend to be ready..."
    for i in {1..30}; do
        if curl -s http://localhost:3000 > /dev/null 2>&1; then
            print_success "Frontend is ready"
            break
        fi
        if [ $i -eq 30 ]; then
            print_warning "Frontend might not be ready yet. You can start it manually with: cd frontend-nextjs && npm run dev"
        fi
        sleep 1
    done
}

# Create sample data
create_sample_data() {
    print_status "Creating sample data..."
    if curl -s -X POST http://localhost:8000/api/v1/demo/create-sample-data > /dev/null; then
        print_success "Sample data created successfully"
    else
        print_warning "Failed to create sample data. You can create it manually later."
    fi
}

# Run system tests
run_tests() {
    print_status "Running system tests..."
    if python3 test_system.py; then
        print_success "All tests passed!"
    else
        print_warning "Some tests failed. Check the output above for details."
    fi
}

# Display system status
show_status() {
    print_status "Displaying system status..."
    python3 status_dashboard.py
}

# Main execution
main() {
    echo "Starting complete system setup..."
    echo
    
    # Pre-flight checks
    check_docker
    check_ports
    echo
    
    # Setup services
    start_services
    echo
    
    # Wait for readiness
    wait_for_services
    echo
    
    # Initialize data
    create_sample_data
    echo
    
    # Test system
    run_tests
    echo
    
    # Show status
    show_status
    echo
    
    print_success "Setup complete! 🎉"
    echo
    echo "🌐 Access your application:"
    echo "   Frontend: http://localhost:3000"
    echo "   Backend API: http://localhost:8000"
    echo "   API Documentation: http://localhost:8000/docs"
    echo "   Test Interface: http://localhost:8000/test"
    echo
    echo "📊 Monitor your system:"
    echo "   Status Dashboard: python3 status_dashboard.py"
    echo "   System Tests: python3 test_system.py"
    echo "   Docker Logs: docker compose logs -f"
    echo
    echo "🛠️  Management Commands:"
    echo "   Stop: docker compose down"
    echo "   Restart: docker compose restart"
    echo "   View Logs: docker compose logs -f [service]"
}

# Run main function
main "$@"
