#!/bin/bash

# QA Agent Launcher Script
# Makes it easy to run any component

cd "$(dirname "$0")"

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║            QA Agent - Agentic Architecture                     ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "What would you like to run?"
echo ""
echo "  1. Setup Wizard (first time setup)"
echo "  2. Full Demo (5 scenarios - recommended)"
echo "  3. Interactive CLI"
echo "  4. API Server"
echo "  5. Test Perception Module"
echo "  6. Test Memory Module"
echo "  7. Test Decision Module"
echo "  8. Test Action Module"
echo "  9. Exit"
echo ""
read -p "Enter your choice (1-9): " choice

case $choice in
    1)
        echo ""
        echo "Running Setup Wizard..."
        python setup.py
        ;;
    2)
        echo ""
        echo "Running Full Demo (this will take 3-5 minutes)..."
        python demo_scenarios.py
        ;;
    3)
        echo ""
        echo "Starting Interactive CLI..."
        python main.py
        ;;
    4)
        echo ""
        echo "Starting API Server at http://localhost:8000"
        echo "Press Ctrl+C to stop"
        python api_server.py
        ;;
    5)
        echo ""
        echo "Testing Perception Module..."
        python perception.py
        ;;
    6)
        echo ""
        echo "Testing Memory Module..."
        python memory.py
        ;;
    7)
        echo ""
        echo "Testing Decision Module..."
        python decision.py
        ;;
    8)
        echo ""
        echo "Testing Action Module..."
        python action.py
        ;;
    9)
        echo ""
        echo "Goodbye!"
        exit 0
        ;;
    *)
        echo ""
        echo "Invalid choice. Please run again."
        exit 1
        ;;
esac

