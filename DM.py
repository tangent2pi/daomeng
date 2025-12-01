import sys
from daomeng.cli import run_cli
from rich.console import Console

console = Console()

def main() -> int:
    try:
        return run_cli()
    except KeyboardInterrupt:
        console.print("\n[bold red]程序已被用户中断。[/bold red]")
        return 1
    except Exception:
        console.print_exception()
        return 1

if __name__ == "__main__":
    sys.exit(main())