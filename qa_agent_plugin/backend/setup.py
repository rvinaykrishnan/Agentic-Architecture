#!/usr/bin/env python3
"""
Setup Script - Get QA Agent Up and Running
This script helps you set up the environment and verify everything works
"""
import os
import sys
import subprocess
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.table import Table

console = Console()

def check_python_version():
    """Check if Python version is adequate"""
    console.print("\n[bold cyan]Step 1: Checking Python Version[/bold cyan]")
    
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        console.print(f"[red]❌ Python {version.major}.{version.minor} detected[/red]")
        console.print("[yellow]Python 3.8 or higher is required[/yellow]")
        return False
    
    console.print(f"[green]✓ Python {version.major}.{version.minor}.{version.micro} - OK[/green]")
    return True

def check_dependencies():
    """Check if required packages are installed"""
    console.print("\n[bold cyan]Step 2: Checking Dependencies[/bold cyan]")
    
    required_packages = [
        'fastapi',
        'uvicorn',
        'pydantic',
        'google.genai',
        'mcp',
        'rich',
        'python-dotenv'
    ]
    
    missing = []
    installed = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            installed.append(package)
            console.print(f"[green]✓ {package}[/green]")
        except ImportError:
            missing.append(package)
            console.print(f"[red]✗ {package}[/red]")
    
    if missing:
        console.print(f"\n[yellow]Missing packages: {', '.join(missing)}[/yellow]")
        if Confirm.ask("\nInstall missing packages now?"):
            console.print("\n[cyan]Installing packages...[/cyan]")
            try:
                subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'], 
                             check=True, capture_output=True)
                console.print("[green]✓ All packages installed![/green]")
                return True
            except subprocess.CalledProcessError as e:
                console.print(f"[red]❌ Installation failed: {e}[/red]")
                return False
        else:
            console.print("\n[yellow]Please install manually:[/yellow]")
            console.print(f"  pip install -r requirements.txt")
            return False
    
    console.print(f"\n[green]✓ All {len(installed)} required packages installed[/green]")
    return True

def setup_env_file():
    """Create .env file with API key"""
    console.print("\n[bold cyan]Step 3: Setting Up Environment Variables[/bold cyan]")
    
    env_file = Path('.env')
    
    if env_file.exists():
        console.print("[yellow]⚠️  .env file already exists[/yellow]")
        if not Confirm.ask("Overwrite existing .env file?"):
            # Read existing key
            with open(env_file, 'r') as f:
                content = f.read()
                if 'GEMINI_API_KEY' in content:
                    console.print("[green]✓ GEMINI_API_KEY found in existing .env[/green]")
                    return True
                else:
                    console.print("[yellow]No GEMINI_API_KEY found in .env[/yellow]")
    
    console.print("\n[bold]Get your Gemini API key from:[/bold]")
    console.print("  https://ai.google.dev/gemini-api/docs/api-key\n")
    
    api_key = Prompt.ask("Enter your GEMINI_API_KEY", password=True)
    
    if not api_key or len(api_key) < 20:
        console.print("[red]❌ Invalid API key[/red]")
        return False
    
    # Write .env file
    with open(env_file, 'w') as f:
        f.write(f"GEMINI_API_KEY={api_key}\n")
    
    console.print("[green]✓ .env file created successfully[/green]")
    return True

def verify_setup():
    """Verify the setup by running a simple test"""
    console.print("\n[bold cyan]Step 4: Verifying Setup[/bold cyan]")
    
    try:
        # Test imports
        console.print("[yellow]→ Testing imports...[/yellow]")
        from perception import UserPreference
        from memory import MemoryAgent
        from decision import DecisionAgent
        from action import ActionAgent
        console.print("[green]✓ All modules import successfully[/green]")
        
        # Test .env loading
        console.print("[yellow]→ Testing environment variables...[/yellow]")
        from dotenv import load_dotenv
        load_dotenv()
        api_key = os.getenv("GEMINI_API_KEY")
        
        if not api_key:
            console.print("[red]❌ GEMINI_API_KEY not found in environment[/red]")
            return False
        
        console.print(f"[green]✓ API key loaded ({api_key[:10]}...)[/green]")
        
        # Test storage directory
        console.print("[yellow]→ Checking storage directory...[/yellow]")
        storage_dir = Path('storage')
        storage_dir.mkdir(exist_ok=True)
        console.print(f"[green]✓ Storage directory ready: {storage_dir.absolute()}[/green]")
        
        # Create logs directory
        console.print("[yellow]→ Creating logs directory...[/yellow]")
        logs_dir = Path('logs')
        logs_dir.mkdir(exist_ok=True)
        console.print(f"[green]✓ Logs directory ready: {logs_dir.absolute()}[/green]")
        
        # Create demo_logs directory
        demo_logs_dir = Path('demo_logs')
        demo_logs_dir.mkdir(exist_ok=True)
        console.print(f"[green]✓ Demo logs directory ready: {demo_logs_dir.absolute()}[/green]")
        
        console.print("\n[bold green]✓ All verifications passed![/bold green]")
        return True
        
    except Exception as e:
        console.print(f"[red]❌ Verification failed: {e}[/red]")
        import traceback
        traceback.print_exc()
        return False

def show_next_steps():
    """Show what to do next"""
    console.print("\n" + "="*70)
    console.print(Panel(
        "[bold green]✓ Setup Complete![/bold green]\n\n"
        "[bold]What to do next:[/bold]\n\n"
        "[cyan]Option 1:[/cyan] Run Interactive CLI\n"
        "  python main.py\n\n"
        "[cyan]Option 2:[/cyan] Run API Server (for Chrome extension)\n"
        "  python api_server.py\n\n"
        "[cyan]Option 3:[/cyan] Run Demo Scenarios (recommended for first time)\n"
        "  python demo_scenarios.py\n\n"
        "[cyan]Option 4:[/cyan] Test individual modules\n"
        "  python perception.py\n"
        "  python memory.py\n"
        "  python decision.py\n"
        "  python action.py\n\n"
        "[yellow]Recommended:[/yellow] Start with demo_scenarios.py to see all features!",
        title="Setup Complete",
        border_style="green"
    ))

def show_quick_test_menu():
    """Show menu for quick testing"""
    console.print("\n[bold]Quick Test Options:[/bold]")
    console.print("1. Run full demo (5 scenarios) - ~3-5 minutes")
    console.print("2. Test single query interactively")
    console.print("3. Start API server")
    console.print("4. Exit and run manually")
    
    choice = Prompt.ask("\nSelect option", choices=["1", "2", "3", "4"], default="1")
    
    return choice

def run_quick_test(choice: str):
    """Run the selected quick test"""
    if choice == "1":
        console.print("\n[bold cyan]Running Full Demo...[/bold cyan]")
        console.print("[yellow]This will take 3-5 minutes and demonstrate all features[/yellow]\n")
        try:
            subprocess.run([sys.executable, 'demo_scenarios.py'], check=True)
        except subprocess.CalledProcessError as e:
            console.print(f"[red]Demo failed: {e}[/red]")
        except KeyboardInterrupt:
            console.print("\n[yellow]Demo interrupted[/yellow]")
    
    elif choice == "2":
        console.print("\n[bold cyan]Starting Interactive Mode...[/bold cyan]\n")
        try:
            subprocess.run([sys.executable, 'main.py'], check=True)
        except subprocess.CalledProcessError as e:
            console.print(f"[red]Interactive mode failed: {e}[/red]")
        except KeyboardInterrupt:
            console.print("\n[yellow]Exited interactive mode[/yellow]")
    
    elif choice == "3":
        console.print("\n[bold cyan]Starting API Server...[/bold cyan]")
        console.print("[yellow]Server will run at http://localhost:8000[/yellow]")
        console.print("[yellow]Press Ctrl+C to stop[/yellow]\n")
        try:
            subprocess.run([sys.executable, 'api_server.py'], check=True)
        except subprocess.CalledProcessError as e:
            console.print(f"[red]Server failed: {e}[/red]")
        except KeyboardInterrupt:
            console.print("\n[yellow]Server stopped[/yellow]")
    
    elif choice == "4":
        console.print("\n[green]Setup complete! Run any script manually.[/green]")

def main():
    """Main setup process"""
    console.print(Panel(
        "[bold cyan]QA Agent - Setup & Installation[/bold cyan]\n\n"
        "This script will help you:\n"
        "• Check Python version\n"
        "• Install dependencies\n"
        "• Set up environment variables\n"
        "• Verify everything works\n"
        "• Run your first test",
        title="Welcome",
        border_style="cyan"
    ))
    
    # Step 1: Check Python
    if not check_python_version():
        console.print("\n[red]Please upgrade Python and try again[/red]")
        return False
    
    # Step 2: Check dependencies
    if not check_dependencies():
        console.print("\n[red]Please install dependencies and try again[/red]")
        return False
    
    # Step 3: Setup .env
    if not setup_env_file():
        console.print("\n[red]Please set up .env file and try again[/red]")
        return False
    
    # Step 4: Verify
    if not verify_setup():
        console.print("\n[red]Setup verification failed[/red]")
        return False
    
    # Show next steps
    show_next_steps()
    
    # Offer quick test
    if Confirm.ask("\nWould you like to run a quick test now?", default=True):
        choice = show_quick_test_menu()
        run_quick_test(choice)
    
    console.print("\n[bold green]✓ All done! Your QA Agent is ready to use.[/bold green]\n")
    return True

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[yellow]Setup interrupted by user[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Setup failed: {e}[/red]")
        import traceback
        traceback.print_exc()

