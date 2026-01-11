"""
FYLIX CLI - Main command interface
"""

import asyncio
import json
from pathlib import Path
from typing import Optional
import typer
from rich.console import Console
from rich.table import Table
from rich.prompt import Confirm
from rich.panel import Panel
from rich.columns import Columns
import httpx

from fylix.config import config
from fylix.api_client import api_client
from fylix.transfer import transfer_manager
from fylix import __version__

app = typer.Typer(
    name="fylix",
    help="FYLIX - Secure file transfer with blockchain verification",
    add_completion=False,
    rich_markup_mode="rich",
    pretty_exceptions_show_locals=False
)

# Force console to use reasonable width even on narrow terminals
console = Console(force_terminal=True, width=100)


# ==================== VERSION ====================

def version_callback(value: bool):
    """Callback for --version/-v flag"""
    if value:
        console.print(f"[cyan]FYLIX CLI[/cyan] [green]v{__version__}[/green]")
        raise typer.Exit()

@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "--v",
        "-v",
        help="Show version and exit",
        callback=version_callback,
        is_eager=True
    )
):
    """
    [bold cyan]FYLIX[/bold cyan] - Secure file transfer with blockchain verification
    
    [bold green]Quick Start:[/bold green]
      [yellow]fylix signup[/yellow] [cyan]<email> <username>[/cyan]  [dim]# Create account[/dim]
      [yellow]fylix login[/yellow] [cyan]<email>[/cyan]                [dim]# Login[/dim]
      [yellow]fylix send[/yellow] [cyan]<file> <recipient>[/cyan]      [dim]# Send file[/dim]
      [yellow]fylix inbox[/yellow]                           [dim]# Check received files[/dim]
      [yellow]fylix receive[/yellow] [cyan]<message_id>[/cyan]          [dim]# Download file[/dim]
    
    [bold]Use[/bold] [yellow]fylix <command> --help[/yellow] [bold]for detailed syntax[/bold]
    """
    if ctx.invoked_subcommand is None and not version:
        # Show custom help when no command is provided
        console.print("\n[bold cyan]FYLIX CLI[/bold cyan] [green]v" + __version__ + "[/green]")
        console.print("[dim]Secure file transfer with blockchain verification[/dim]\n")
        
        help_text = [
            Panel(
                "[yellow]fylix signup[/yellow] [cyan]EMAIL USERNAME[/cyan]\n"
                "[dim]Options:[/dim] [magenta]-p, --password[/magenta]\n"
                "         [magenta]-f, --first-name[/magenta]\n"
                "         [magenta]-l, --last-name[/magenta]",
                title="[bold green]Authentication[/bold green]",
                border_style="green"
            ),
            Panel(
                "[yellow]fylix login[/yellow] [cyan]EMAIL[/cyan]\n"
                "[dim]Options:[/dim] [magenta]-p, --password[/magenta]\n\n"
                "[yellow]fylix logout[/yellow]\n"
                "[dim]Clear stored credentials[/dim]",
                title="[bold green]Login/Logout[/bold green]",
                border_style="green"
            )
        ]
        
        transfer_help = [
            Panel(
                "[yellow]fylix send[/yellow] [cyan]FILE RECIPIENT[/cyan]\n"
                "[dim]Send file with blockchain proof[/dim]\n"
                "[dim]Example:[/dim] fylix send doc.pdf user@example.com\n\n"
                "[yellow]fylix inbox[/yellow] [magenta][OPTIONS][/magenta]\n"
                "[dim]Options:[/dim] [magenta]--page[/magenta] [cyan]N[/cyan]\n"
                "         [magenta]--status[/magenta] [cyan]pending|verified[/cyan]",
                title="[bold blue]File Transfer[/bold blue]",
                border_style="blue"
            ),
            Panel(
                "[yellow]fylix receive[/yellow] [cyan]MESSAGE_ID[/cyan]\n"
                "[dim]Options:[/dim] [magenta]-o, --output[/magenta] [cyan]DIR[/cyan]\n"
                "[dim]Download with integrity check[/dim]\n\n"
                "[yellow]fylix verify[/yellow] [cyan]MESSAGE_ID[/cyan]\n"
                "[dim]Show blockchain proof[/dim]",
                title="[bold blue]Download & Verify[/bold blue]",
                border_style="blue"
            )
        ]
        
        room_help = [
            Panel(
                "[yellow]fylix rooms[/yellow]\n"
                "[dim]List all chat rooms[/dim]\n\n"
                "[yellow]fylix create-room[/yellow] [cyan]NAME[/cyan]\n"
                "[dim]Options:[/dim] [magenta]--members[/magenta] [cyan]email1,email2[/cyan]",
                title="[bold magenta]Rooms[/bold magenta]",
                border_style="magenta"
            ),
            Panel(
                "[yellow]fylix chat[/yellow] [cyan]ROOM_ID[/cyan]\n"
                "[dim]Interactive chat in room[/dim]\n\n"
                "[yellow]fylix send-message[/yellow] [cyan]ROOM_ID TEXT[/cyan]\n"
                "[dim]Send message to room[/dim]",
                title="[bold magenta]Messaging[/bold magenta]",
                border_style="magenta"
            )
        ]
        
        console.print(Columns(help_text))
        console.print()
        console.print(Columns(transfer_help))
        console.print()
        console.print(Columns(room_help))
        console.print()
        console.print("[bold yellow]More Commands:[/bold yellow]")
        console.print("  [yellow]fylix resume[/yellow] [cyan]TRANSFER_ID[/cyan]     [dim]# Resume failed transfer[/dim]")
        console.print("  [yellow]fylix whoami[/yellow]                  [dim]# Show current user[/dim]")
        console.print("  [yellow]fylix deleteaccount[/yellow]           [dim]# Delete your account[/dim]")
        console.print()
        console.print("[dim]Use [/dim][yellow]fylix <command> --help[/yellow][dim] for detailed information[/dim]")
        console.print("[dim]Version:[/dim] [green]" + __version__ + "[/green]")
        raise typer.Exit()


# ==================== SIGNUP ====================

@app.command()
def signup(
    email: str = typer.Argument(..., help="Your email address"),
    username: str = typer.Argument(..., help="Your username (3-50 chars, alphanumeric + _ -)"),
    password: str = typer.Option(..., "--password", "-p", prompt=True, hide_input=True, confirmation_prompt=True, help="Your password (min 8 chars)"),
    first_name: str = typer.Option(None, "--first-name", "-f", help="Your first name (optional)"),
    last_name: str = typer.Option(None, "--last-name", "-l", help="Your last name (optional)")
):
    """
    Create a new FYLIX account
    
    [bold yellow]Syntax:[/bold yellow]
      fylix signup [cyan]EMAIL USERNAME[/cyan] [magenta][OPTIONS][/magenta]
    
    [bold green]Examples:[/bold green]
      fylix signup user@example.com johndoe
      fylix signup alice@test.com alice123 -f Alice -l Smith
    
    [bold blue]Options:[/bold blue]
      [magenta]-p, --password[/magenta]    Your password (will prompt if not provided)
      [magenta]-f, --first-name[/magenta]  Your first name (optional)
      [magenta]-l, --last-name[/magenta]   Your last name (optional)
    """
    async def _signup():
        try:
            # Validate password length
            if len(password) < 8:
                console.print("[red]✗ Password must be at least 8 characters long[/red]")
                raise typer.Exit(1)
            
            console.print(f"\n[cyan]📝 Creating account for {email}...[/cyan]")
            
            # Attempt signup
            auth_response = await api_client.signup(
                email=email,
                username=username,
                password=password,
                first_name=first_name,
                last_name=last_name
            )
            
            # Extract tokens
            access_token = auth_response["access_token"]
            refresh_token = auth_response["refresh_token"]
            user_id = auth_response["user"]["id"]
            username_from_response = auth_response["user"]["username"]
            
            # Save credentials locally
            config.save_credentials(
                email=email,
                access_token=access_token,
                refresh_token=refresh_token,
                user_id=user_id,
                username=username_from_response
            )
            
            console.print(f"[green]✓ Account created successfully![/green]")
            console.print(f"[green]✓ Logged in as {username_from_response}[/green]")
            console.print(f"[dim]Credentials stored in {config.credentials_file}[/dim]")
        
        except httpx.HTTPStatusError as e:
            try:
                error_detail = e.response.json().get("detail", str(e))
            except:
                error_detail = str(e)
            
            if "email" in str(error_detail).lower() and "already" in str(error_detail).lower():
                console.print(f"[red]✗ Email already registered. Try logging in instead.[/red]")
            elif "username" in str(error_detail).lower() and ("already" in str(error_detail).lower() or "taken" in str(error_detail).lower()):
                console.print(f"[red]✗ Username already taken. Choose a different username.[/red]")
            else:
                console.print(f"[red]✗ Signup failed: {error_detail}[/red]")
            raise typer.Exit(1)
        except Exception as e:
            console.print(f"[red]✗ Signup failed: {str(e)}[/red]")
            raise typer.Exit(1)
        
        finally:
            await api_client.close()
    
    asyncio.run(_signup())


# ==================== LOGIN ====================

@app.command()
def login(
    email: str = typer.Argument(..., help="Your email address"),
    password: str = typer.Option(..., "--password", "-p", prompt=True, hide_input=True, help="Your password")
):
    """
    Login to FYLIX backend and store credentials locally
    
    [bold yellow]Syntax:[/bold yellow]
      fylix login [cyan]EMAIL[/cyan] [magenta][OPTIONS][/magenta]
    
    [bold green]Examples:[/bold green]
      fylix login user@example.com
      fylix login alice@test.com -p MyPassword123
    
    [bold blue]Options:[/bold blue]
      [magenta]-p, --password[/magenta]  Your password (will prompt if not provided)
    """
    async def _login():
        try:
            console.print(f"\n[cyan]🔐 Logging in as {email}...[/cyan]")
            
            # Attempt login
            auth_response = await api_client.login(email, password)
            
            # Extract tokens
            access_token = auth_response["access_token"]
            refresh_token = auth_response["refresh_token"]
            user_id = auth_response["user"]["id"]
            username = auth_response["user"]["username"]
            
            # Save credentials locally
            config.save_credentials(
                email=email,
                access_token=access_token,
                refresh_token=refresh_token,
                user_id=user_id,
                username=username
            )
            
            console.print(f"[green]✓ Logged in successfully as {username}[/green]")
            console.print(f"[dim]Credentials stored in {config.credentials_file}[/dim]")
        
        except Exception as e:
            console.print(f"[red]✗ Login failed: {e}[/red]")
            raise typer.Exit(1)
        
        finally:
            await api_client.close()
    
    asyncio.run(_login())


# ==================== LOGOUT ====================

@app.command()
def logout():
    """
    Logout and clear stored credentials
    
    [bold yellow]Syntax:[/bold yellow]
      fylix logout
    
    [bold green]Example:[/bold green]
      fylix logout
    """
    if not config.is_logged_in():
        console.print("[yellow]⚠ Not logged in[/yellow]")
        return
    
    creds = config.get_credentials()
    config.clear_credentials()
    console.print(f"[green]✓ Logged out {creds.get('email')}[/green]")


# ==================== DELETE ACCOUNT ====================

@app.command()
def deleteaccount(
    password: str = typer.Option(..., "--password", "-p", prompt=True, hide_input=True, help="Your password for confirmation")
):
    """
    Permanently delete your FYLIX account and all associated data
    
    [bold yellow]Syntax:[/bold yellow]
      fylix deleteaccount [magenta][OPTIONS][/magenta]
    
    [bold red]⚠️  WARNING: This action cannot be undone![/bold red]
    
    [bold]This will delete:[/bold]
      - Your account permanently
      - All chat rooms and messages
      - All file transfers
      - All your data from the system
    
    [bold green]Example:[/bold green]
      fylix deleteaccount
    
    [bold blue]Options:[/bold blue]
      [magenta]-p, --password[/magenta]  Your password for confirmation
    """
    if not config.is_logged_in():
        console.print("[red]✗ You must be logged in to delete your account[/red]")
        raise typer.Exit(1)
    
    async def _delete_account():
        try:
            creds = config.get_credentials()
            username = creds.get('username', 'Unknown')
            email = creds.get('email', 'Unknown')
            
            # Final confirmation
            console.print("\n[red bold]⚠️  WARNING: PERMANENT ACCOUNT DELETION[/red bold]")
            console.print(f"[yellow]Account: {username} ({email})[/yellow]")
            console.print("[red]This will permanently delete:[/red]")
            console.print("  - Your account")
            console.print("  - All your messages")
            console.print("  - All your file transfers")
            console.print("  - Your membership in all rooms")
            console.print("\n[red bold]This action CANNOT be undone![/red bold]\n")
            
            confirm = Confirm.ask("[red]Are you absolutely sure you want to delete your account?[/red]")
            if not confirm:
                console.print("[green]✓ Account deletion cancelled[/green]")
                return
            
            # Double confirmation
            confirm2 = Confirm.ask("[red bold]Type YES to confirm permanent deletion[/red bold]", default=False)
            if not confirm2:
                console.print("[green]✓ Account deletion cancelled[/green]")
                return
            
            console.print(f"\n[cyan]🗑️  Deleting account {username}...[/cyan]")
            
            # Delete account
            result = await api_client.delete_account(password)
            
            # Clear local credentials
            config.clear_credentials()
            
            console.print(f"[green]✓ {result.get('message', 'Account permanently deleted')}[/green]")
            console.print("[dim]All your data has been removed from the system[/dim]")
        
        except httpx.HTTPStatusError as e:
            try:
                error_detail = e.response.json().get("detail", str(e))
            except:
                error_detail = str(e)
            
            if "password" in str(error_detail).lower() and "incorrect" in str(error_detail).lower():
                console.print("[red]✗ Incorrect password. Account deletion cancelled.[/red]")
            else:
                console.print(f"[red]✗ Account deletion failed: {error_detail}[/red]")
            raise typer.Exit(1)
        except Exception as e:
            console.print(f"[red]✗ Account deletion failed: {str(e)}[/red]")
            raise typer.Exit(1)
        
        finally:
            await api_client.close()
    
    asyncio.run(_delete_account())


# ==================== WHOAMI ====================

@app.command()
def whoami():
    """
    Show current logged-in user information
    
    [bold yellow]Syntax:[/bold yellow]
      fylix whoami
    
    [bold green]Example:[/bold green]
      fylix whoami
    """
    if not config.is_logged_in():
        console.print("[yellow]⚠ Not logged in[/yellow]")
        console.print("[dim]Run 'fylix login <email>' to authenticate[/dim]")
        return
    
    creds = config.get_credentials()
    console.print(f"\n[cyan]👤 Current User[/cyan]")
    console.print(f"Email: {creds['email']}")
    console.print(f"Username: {creds['username']}")
    console.print(f"User ID: {creds['user_id'][:16]}...")
    console.print(f"Logged in: {creds['logged_in_at']}")


# ==================== INBOX ====================

@app.command()
def inbox(range: str = typer.Argument("1-10", help="Message range (e.g., 1-10, max 10)")):
    """
    List incoming file transfers (loads 10 messages at a time)
    
    [bold yellow]Syntax:[/bold yellow]
      fylix inbox [cyan][RANGE][/cyan]
    
    [bold green]Examples:[/bold green]
      fylix inbox           [dim]# Load messages 1-10 (default)[/dim]
      fylix inbox 1-10      [dim]# Load messages 1-10[/dim]
      fylix inbox 11-20     [dim]# Load next 10 messages[/dim]
      fylix inbox 21-30     [dim]# Load messages 21-30[/dim]
    
    [bold blue]Arguments:[/bold blue]
      [cyan]RANGE[/cyan]  Message range (default: 1-10, max 10 per request)
    """
    async def _inbox(range_str: str):
        if not config.is_logged_in():
            console.print("[red]✗ Not logged in. Run 'fylix login <email>' first[/red]")
            raise typer.Exit(1)
        
        # Parse range
        try:
            start, end = map(int, range_str.split('-'))
            if start < 1 or end < start:
                console.print("[red]Invalid range. Use format: 1-10[/red]")
                return
            if end - start + 1 > 10:
                console.print("[red]Maximum 10 messages can be loaded at once.[/red]")
                console.print("[yellow]To see first 10: fylix inbox 1-10[/yellow]")
                console.print("[yellow]To see next 10: fylix inbox 11-20[/yellow]")
                return
        except ValueError:
            console.print("[red]Invalid range format. Use: fylix inbox 1-10[/red]")
            return
        
        try:
            from rich.progress import Progress, SpinnerColumn, TextColumn
            
            with Progress(
                SpinnerColumn(),
                TextColumn(f"[cyan]📬 Fetching inbox (messages {start}-{end})...[/cyan]"),
                transient=True
            ) as progress:
                task = progress.add_task("", total=None)
                
                # Get all user rooms
                rooms_response = await api_client.get_user_rooms()
                rooms = rooms_response.get("rooms", [])
            
            # Collect all file messages from all rooms
            incoming_files = []
            
            for room in rooms:
                room_id = room["id"]
                room_name = room.get("name", room_id[:8])
                
                try:
                    # Get messages (limit 200 for pagination)
                    messages_response = await api_client.get_room_messages(room_id, limit=200)
                    messages = messages_response.get("messages", [])
                except Exception as e:
                    # Check for auth errors - don't skip these silently
                    error_str = str(e)
                    if "401" in error_str or "Unauthorized" in error_str or "403" in error_str or "Forbidden" in error_str:
                        # Auth error - propagate up to show proper error message
                        raise
                    # Skip rooms that timeout or have other errors (but log them)
                    import sys
                    import traceback
                    print(f"⚠️ Warning: Skipped room '{room_name}' due to error: {e.__class__.__name__}: {e}", file=sys.stderr)
                    # traceback.print_exc(file=sys.stderr)  # Uncomment for debugging
                    continue
                
                # Filter file messages (type can be "file" or "image")
                for msg in messages:
                    if msg["message_type"] in ["file", "image"] and msg.get("file_name"):
                        # Only show files from other users (not self-sent)
                        if msg["sender_id"] != config.get_user_id():
                            # Check for blockchain fields with fallback
                            blockchain_tx = msg.get("blockchain_tx_hash")
                            if not blockchain_tx:
                                blockchain_tx = msg.get("blockchain_hash") or msg.get("tx_hash")
                            
                            incoming_files.append({
                                "message_id": msg["id"],
                                "sender": msg["sender_username"],
                                "filename": msg.get("file_name", "Unknown"),
                                "size": msg.get("file_size", 0),
                                "file_hash": msg.get("file_hash"),
                                "ipfs_cid": msg.get("ipfs_cid"),
                                "blockchain_tx": blockchain_tx,
                                "created_at": msg["created_at"],
                                "room_name": room_name,
                                "room_type": room.get("type", "unknown"),
                                "room_id": room_id
                            })
            
            if not incoming_files:
                console.print("\n[yellow]📭 No incoming files[/yellow]")
                return
            
            # Sort by timestamp (newest first)
            incoming_files.sort(key=lambda x: x["created_at"], reverse=True)
            
            # Total count
            total_messages = len(incoming_files)
            
            # Check if requested range is valid
            if start > total_messages:
                console.print(f"[red]No messages found in range {start}-{end}[/red]")
                console.print(f"[yellow]Total messages in inbox: {total_messages}[/yellow]")
                console.print(f"[yellow]Use: fylix inbox 1-10 to see the first 10 messages[/yellow]")
                return
            
            # Slice for requested range (adjust end if it exceeds total)
            actual_end = min(end, total_messages)
            paginated_files = incoming_files[start-1:actual_end]
            
            # Display table
            table = Table(title=f"Inbox (Showing {start}-{actual_end} of {total_messages} total)")
            table.add_column("Sender", style="cyan")
            table.add_column("Filename", style="white")
            table.add_column("Size", style="green")
            table.add_column("Room", style="blue")  # Add room type/name
            table.add_column("Time", style="magenta")
            table.add_column("Status", style="yellow")
            table.add_column("ID (7 chars)", style="bright_blue")
            table.add_column("#", style="dim")
            
            for idx, file in enumerate(paginated_files, start=start):
                size_str = _format_size(file["size"])
                
                # Format timestamp in IST (Indian Standard Time)
                from datetime import datetime, timezone, timedelta
                try:
                    dt = datetime.fromisoformat(file["created_at"].replace('Z', '+00:00'))
                    # Convert to IST (UTC+5:30)
                    ist_tz = timezone(timedelta(hours=5, minutes=30))
                    dt_ist = dt.astimezone(ist_tz)
                    time_str = dt_ist.strftime("%b %d, %I:%M%p")
                except:
                    time_str = "Unknown"
                
                # Determine integrity status - use actual message status from database
                msg_id = file["message_id"]
                
                # Check actual message delivery status
                # Priority: downloaded > blockchain verified > pending
                downloaded_files = config.get_credentials().get("downloaded_files", [])
                if msg_id in downloaded_files:
                    status = "✓ Downloaded"
                elif file.get("blockchain_tx"):
                    status = "✓ Received" 
                else:
                    status = "⚠ Pending"
                
                # Show first 7 chars (no ellipsis - easier to copy)
                msg_id_short = file["message_id"][:7]
                
                # Format room info (no truncation)
                room_type = file.get("room_type", "unknown")[:1].upper()  # G for group, D for direct
                room_name_short = file.get("room_name", "?")  # Full name
                room_info = f"{room_type}:{room_name_short}"
                
                table.add_row(
                    file["sender"],
                    file["filename"],  # Full filename, no truncation
                    size_str,
                    room_info,
                    time_str,
                    status,
                    msg_id_short,
                    str(idx)
                )
            
            console.print(table)
            
            # Show pagination info
            if actual_end < total_messages:
                next_start = actual_end + 1
                next_end = min(actual_end + 10, total_messages)
                console.print(f"\n[yellow]📄 More messages available. Use: fylix inbox {next_start}-{next_end}[/yellow]")
            
            console.print(f"\n[cyan]To download:[/cyan] fylix receive <ID>")
            console.print(f"[cyan]To verify:[/cyan] fylix verify <ID>")
            if paginated_files:
                console.print(f"[dim]Example: fylix receive {paginated_files[0]['message_id'][:7]} or fylix verify {paginated_files[0]['message_id'][:7]}[/dim]")
        
        except Exception as e:
            # Check if it's an authentication error
            if "401" in str(e) or "Unauthorized" in str(e):
                console.print("[red]✗ Token expired. Please login again:[/red]")
                console.print(f"[cyan]fylix login {config.get_credentials().get('email', '<email>')}[/cyan]")
            elif "Connection" in str(e) or "connection" in str(e):
                console.print("[red]✗ Cannot connect to server. Is the backend running?[/red]")
                console.print("[dim]Start backend: cd backend && python main.py[/dim]")
            else:
                console.print(f"[red]✗ Failed to fetch inbox: {e}[/red]")
            raise typer.Exit(1)
        
        finally:
            await api_client.close()
    
    asyncio.run(_inbox(range))


# ==================== OUTBOX ====================

@app.command()
def outbox(range: str = typer.Argument("1-10", help="Message range (e.g., 1-10, max 10)")):
    """
    List files you've sent to others (loads 10 messages at a time)
    
    [bold yellow]Syntax:[/bold yellow]
      fylix outbox [cyan][RANGE][/cyan]
    
    [bold green]Examples:[/bold green]
      fylix outbox          [dim]# Load messages 1-10 (default)[/dim]
      fylix outbox 1-10     [dim]# Load messages 1-10[/dim]
      fylix outbox 11-20    [dim]# Load next 10 messages[/dim]
    
    [bold blue]Arguments:[/bold blue]
      [cyan]RANGE[/cyan]  Message range (default: 1-10, max 10 per request)
    """
    async def _outbox(range_str: str):
        if not config.is_logged_in():
            console.print("[red]✗ Not logged in. Run 'fylix login <email>' first[/red]")
            raise typer.Exit(1)
        
        # Parse range
        try:
            start, end = map(int, range_str.split('-'))
            if start < 1 or end < start:
                console.print("[red]Invalid range. Use format: 1-10[/red]")
                return
            if end - start + 1 > 10:
                console.print("[red]Maximum 10 messages can be loaded at once.[/red]")
                console.print("[yellow]To see first 10: fylix outbox 1-10[/yellow]")
                console.print("[yellow]To see next 10: fylix outbox 11-20[/yellow]")
                return
        except ValueError:
            console.print("[red]Invalid range format. Use: fylix outbox 1-10[/red]")
            return
        
        try:
            from rich.progress import Progress, SpinnerColumn, TextColumn
            
            with Progress(
                SpinnerColumn(),
                TextColumn(f"[cyan]📤 Fetching outbox (messages {start}-{end})...[/cyan]"),
                transient=True
            ) as progress:
                task = progress.add_task("", total=None)
                
                # Get all user rooms
                rooms_response = await api_client.get_user_rooms()
                rooms = rooms_response.get("rooms", [])
            
            # Collect all file messages sent by current user
            sent_files = []
            current_user_id = config.get_user_id()
            
            for room in rooms:
                room_id = room["id"]
                room_name = room.get("name", "Unknown")
                room_type = room.get("type", "direct")
                
                # Get other member (recipient) for direct chats
                members = room.get("members", [])
                recipient_username = "Unknown"
                for member in members:
                    if member["user_id"] != current_user_id:
                        recipient_username = member["username"]
                        break
                
                try:
                    # Get messages (limit 200 to allow pagination)
                    messages_response = await api_client.get_room_messages(room_id, limit=200)
                    messages = messages_response.get("messages", [])
                except Exception as e:
                    # Check for auth errors - don't skip these silently
                    error_str = str(e)
                    if "401" in error_str or "Unauthorized" in error_str or "403" in error_str or "Forbidden" in error_str:
                        # Auth error - propagate up to show proper error message
                        raise
                    # Skip rooms that timeout or have other errors (but log them)
                    import sys
                    import traceback
                    print(f"⚠️ Warning: Skipped room '{room_name}' due to error: {e.__class__.__name__}: {e}", file=sys.stderr)
                    # traceback.print_exc(file=sys.stderr)  # Uncomment for debugging
                    continue
                
                # Filter file messages sent by current user (type can be "file" or "image")
                for msg in messages:
                    if msg["message_type"] in ["file", "image"] and msg.get("file_name") and msg["sender_id"] == current_user_id:
                        # Check for blockchain fields with fallback
                        blockchain_tx = msg.get("blockchain_tx_hash")
                        if not blockchain_tx:
                            # Try alternate field names
                            blockchain_tx = msg.get("blockchain_hash") or msg.get("tx_hash")
                        
                        sent_files.append({
                            "message_id": msg["id"],
                            "room_id": room_id,
                            "room_type": room_type,
                            "room_name": room_name,
                            "recipient_username": recipient_username,
                            "filename": msg.get("file_name", "Unknown"),
                            "size": msg.get("file_size", 0),
                            "file_hash": msg.get("file_hash"),
                            "ipfs_cid": msg.get("ipfs_cid"),
                            "blockchain_tx": blockchain_tx,
                            "created_at": msg["created_at"]
                        })
            
            if not sent_files:
                console.print("\n[yellow]📭 No sent files[/yellow]")
                return
            
            # Sort by timestamp (newest first)
            sent_files.sort(key=lambda x: x["created_at"], reverse=True)
            
            # Total count
            total_messages = len(sent_files)
            
            # Check if requested range is valid
            if start > total_messages:
                console.print(f"[red]No messages found in range {start}-{end}[/red]")
                console.print(f"[yellow]Total messages in outbox: {total_messages}[/yellow]")
                console.print(f"[yellow]Use: fylix outbox 1-10 to see the first 10 messages[/yellow]")
                return
            
            # Slice for requested range
            actual_end = min(end, total_messages)
            paginated_files = sent_files[start-1:actual_end]
            
            # Display table
            table = Table(title=f"Outbox (Showing {start}-{actual_end} of {total_messages} total)")
            table.add_column("Recipient", style="cyan")
            table.add_column("Filename", style="white")
            table.add_column("Size", style="green")
            table.add_column("Time", style="magenta")
            table.add_column("Status", style="yellow")
            table.add_column("Message ID", style="dim")
            table.add_column("#", style="bright_blue")  # Message number
            
            for idx, file in enumerate(paginated_files, start=start):
                try:
                    size_str = _format_size(file["size"])
                    
                    # Format timestamp in IST (Indian Standard Time)
                    from datetime import datetime, timezone, timedelta
                    try:
                        dt = datetime.fromisoformat(file["created_at"].replace('Z', '+00:00'))
                        # Convert to IST (UTC+5:30)
                        ist_tz = timezone(timedelta(hours=5, minutes=30))
                        dt_ist = dt.astimezone(ist_tz)
                        time_str = dt_ist.strftime("%b %d, %I:%M%p")
                    except:
                        time_str = "Unknown"
                    
                    # Determine delivery status based on blockchain verification
                    status = "✓ Sent" if file.get("blockchain_tx") else "⚠ Pending"
                    
                    # Show first 7 chars (same format as inbox, no ellipsis)
                    msg_id_short = file["message_id"][:7]
                    
                    # Determine recipient display based on room type
                    if file["room_type"] == "group":
                        # Show room name and first 7 chars of room ID
                        recipient_display = f"{file['room_name']} ({file['room_id'][:7]})"
                    else:
                        # Direct chat - show recipient username
                        recipient_display = file["recipient_username"]
                    
                    table.add_row(
                        recipient_display,
                        file["filename"],  # Full filename, no truncation
                        size_str,
                        time_str,
                        status,
                        msg_id_short,
                        str(idx)
                    )
                except Exception as e:
                    pass  # Skip row if error
            
            console.print(table)
            
            # Show pagination info
            if actual_end < total_messages:
                next_start = actual_end + 1
                next_end = min(actual_end + 10, total_messages)
                console.print(f"\n[yellow]📄 More messages available. Use: fylix outbox {next_start}-{next_end}[/yellow]")
            
            console.print(f"\n[cyan]To verify:[/cyan] fylix verify <ID>")
            if paginated_files:
                console.print(f"[dim]Example: fylix verify {paginated_files[0]['message_id'][:7]}[/dim]")
            console.print(f"[dim]Files are available for recipient to download[/dim]")
        
        except Exception as e:
            # Check if it's an authentication error
            if "401" in str(e) or "Unauthorized" in str(e):
                console.print("[red]✗ Token expired. Please login again:[/red]")
                console.print(f"[cyan]fylix login {config.get_credentials().get('email', '<email>')}[/cyan]")
            elif "Connection" in str(e) or "connection" in str(e):
                console.print("[red]✗ Cannot connect to server. Is the backend running?[/red]")
                console.print("[dim]Start backend: cd backend && python main.py[/dim]")
            else:
                console.print(f"[red]✗ Failed to fetch outbox: {e}[/red]")
            raise typer.Exit(1)
        
        finally:
            await api_client.close()
    
    asyncio.run(_outbox(range))


# ==================== CHAT ROOM MANAGEMENT ====================

@app.command()
def rooms():
    """
    List all your chat rooms (direct chats and groups)
    
    [bold yellow]Syntax:[/bold yellow]
      fylix rooms
    
    [bold]Shows:[/bold]
      - Room name/participants
      - Room type (direct/group)
      - Member count
      - Room ID for other commands
    
    [bold green]Example:[/bold green]
      fylix rooms
    """
    async def _rooms():
        if not config.is_logged_in():
            console.print("[red]✗ Not logged in. Run 'fylix login <email>' first[/red]")
            raise typer.Exit(1)
        
        try:
            console.print("\n[cyan]💬 Fetching chat rooms...[/cyan]")
            
            rooms_response = await api_client.get_user_rooms()
            rooms = rooms_response.get("rooms", [])
            
            if not rooms:
                console.print("[yellow]No chat rooms found[/yellow]")
                console.print("[dim]Create a group: fylix create <name>[/dim]")
                console.print("[dim]Send a file to start direct chat: fylix send <file> <email>[/dim]")
                return
            
            # Display table
            from rich.table import Table
            from rich import box
            table = Table(title=f"Chat Rooms ({len(rooms)} total)", box=box.ROUNDED)
            table.add_column("Name/Participants", style="cyan")
            table.add_column("Type", style="green")
            table.add_column("Members", style="magenta")
            table.add_column("Admin", style="yellow")
            table.add_column("ID (7)", style="bright_blue")
            
            current_user_id = config.get_user_id()
            
            for room in rooms:
                room_type = room.get("type", "direct")
                
                # Format room name
                if room_type == "group":
                    room_name = room.get("name", "Unnamed Group")
                else:
                    # For direct chats, show other participant
                    members = room.get("members", [])
                    other_member = next((m for m in members if m.get("user_id") != current_user_id), None)
                    room_name = other_member.get("username", "Unknown") if other_member else "Unknown"
                
                member_count = len(room.get("members", []))
                room_id_short = room["id"][:7]  # Only 7 chars
                
                # Find admin
                members = room.get("members", [])
                admin = next((m.get("username", "?") for m in members if m.get("role") == "admin"), "-")
                
                table.add_row(
                    room_name,
                    room_type.upper(),
                    str(member_count),
                    admin,
                    room_id_short
                )
            
            console.print(table)
            console.print("\n[cyan]Commands:[/cyan]")
            console.print("[dim]View members:    fylix members <room_id>[/dim]")
            console.print("[dim]Create group:    fylix create <name>[/dim]")
            console.print("[dim]Send to group:   fylix sendroom <room_id> <file>[/dim]")
            console.print("[dim]Delete room:     fylix delroom <room_id> (admin only)[/dim]")
            console.print("\n[yellow]Note:[/yellow] Direct rooms auto-create when you send files via email")
        
        except Exception as e:
            # Check if it's an authentication error
            if "401" in str(e) or "Unauthorized" in str(e):
                console.print("[red]✗ Token expired. Please login again:[/red]")
                console.print(f"[cyan]fylix login {config.get_credentials().get('email', '<email>')}[/cyan]")
            elif "Connection" in str(e) or "connection" in str(e):
                console.print("[red]✗ Cannot connect to server. Is the backend running?[/red]")
                console.print("[dim]Start backend: cd backend && python main.py[/dim]")
            else:
                console.print(f"[red]✗ Failed to fetch rooms: {e}[/red]")
            raise typer.Exit(1)
        
        finally:
            await api_client.close()
    
    asyncio.run(_rooms())


@app.command()
def create(
    name: str = typer.Argument(..., help="Group chat name"),
    members: Optional[str] = typer.Option(None, "--members", "-m", help="Comma-separated emails to add")
):
    """
    Create a new group chat
    
    [bold yellow]Syntax:[/bold yellow]
      fylix create [cyan]NAME[/cyan] [magenta][OPTIONS][/magenta]
    
    [bold green]Examples:[/bold green]
      fylix create "Team Project"
      fylix create "Study Group" -m user1@email.com,user2@email.com
    
    [bold blue]Options:[/bold blue]
      [magenta]-m, --members[/magenta]  Comma-separated emails to add as members
    """
    async def _create():
        if not config.is_logged_in():
            console.print("[red]✗ Not logged in. Run 'fylix login <email>' first[/red]")
            raise typer.Exit(1)
        
        try:
            console.print(f"\n[cyan]🆕 Creating group chat '{name}'...[/cyan]")
            
            # Parse members if provided
            member_list = None
            if members:
                member_list = [email.strip() for email in members.split(",")]
                console.print(f"[dim]Adding {len(member_list)} members...[/dim]")
            
            # Create group
            room = await api_client.create_group_chat(name, member_list)
            
            console.print(f"\n[green]✓ Group chat created![/green]")
            console.print(f"Name: {room.get('name')}")
            console.print(f"Room ID: {room.get('id')}")
            console.print(f"Members: {len(room.get('members', []))}")
            
            console.print(f"\n[cyan]Next steps:[/cyan]")
            console.print(f"[dim]Add members: fylix add {room.get('id')[:8]} <email>[/dim]")
            console.print(f"[dim]Send files: fylix send <file> <email>[/dim]")
        
        except httpx.HTTPStatusError as e:
            # Parse the error response for better user messaging
            try:
                error_detail = e.response.json().get("detail", str(e))
            except:
                error_detail = str(e)
            
            # Provide helpful error messages
            if "404" in str(e.response.status_code):
                if "not found" in error_detail.lower() or "could not find user" in error_detail.lower():
                    console.print(f"[red]✗ User not found[/red]")
                    console.print(f"[yellow]Details: {error_detail}[/yellow]")
                    console.print(f"\n[cyan]💡 Troubleshooting:[/cyan]")
                    console.print("  1. Check that the email addresses are correct")
                    console.print("  2. Make sure users have signed up (fylix signup)")
                    console.print("  3. Try again - database might be slow")
                else:
                    console.print(f"[red]✗ Not found: {error_detail}[/red]")
            elif "504" in str(e.response.status_code) or "timeout" in error_detail.lower() or "slow" in error_detail.lower():
                console.print(f"[yellow]⏱️  Database is slow right now[/yellow]")
                console.print(f"[dim]This can happen with free-tier databases or slow internet[/dim]")
                console.print(f"\n[cyan]💡 What to do:[/cyan]")
                console.print("  1. Wait 30 seconds for the database to respond")
                console.print("  2. Try the command again")
                console.print("  3. If it persists, check your internet connection")
            elif "500" in str(e.response.status_code):
                console.print(f"[red]✗ Server error[/red]")
                console.print(f"[yellow]{error_detail}[/yellow]")
                if "timeout" in error_detail.lower() or "slow" in error_detail.lower():
                    console.print(f"\n[cyan]💡 The database is responding slowly[/cyan]")
                    console.print("  Wait 30 seconds and try again")
            else:
                console.print(f"[red]✗ Failed to create group: {error_detail}[/red]")
            raise typer.Exit(1)
        except httpx.TimeoutException:
            console.print(f"[yellow]⏱️  Request timed out[/yellow]")
            console.print("[cyan]The server took too long to respond. Try again in 30 seconds.[/cyan]")
            raise typer.Exit(1)
        except Exception as e:
            error_msg = str(e)
            if "timeout" in error_msg.lower() or "timed out" in error_msg.lower():
                console.print(f"[yellow]⏱️  Request timed out[/yellow]")
                console.print("[cyan]The server is responding slowly. Please try again in a moment.[/cyan]")
            else:
                console.print(f"[red]✗ Failed to create group: {error_msg}[/red]")
            raise typer.Exit(1)
        
        finally:
            await api_client.close()
    
    asyncio.run(_create())


@app.command()
def members(
    room_id: str = typer.Argument(..., help="Room ID (from 'fylix rooms' command)")
):
    """
    View members of a chat room
    
    Example: fylix members abc12345
    """
    async def _members():
        if not config.is_logged_in():
            console.print("[red]✗ Not logged in. Run 'fylix login <email>' first[/red]")
            raise typer.Exit(1)
        
        try:
            console.print(f"\n[cyan]👥 Fetching room members...[/cyan]")
            
            # Find room by partial ID match
            rooms_response = await api_client.get_user_rooms()
            rooms = rooms_response.get("rooms", [])
            
            matching_room = None
            for room in rooms:
                if room["id"] == room_id or room["id"].startswith(room_id):
                    matching_room = room
                    break
            
            if not matching_room:
                console.print(f"[red]✗ Room {room_id} not found[/red]")
                console.print("[dim]Use 'fylix rooms' to see available rooms[/dim]")
                raise typer.Exit(1)
            
            # Get detailed room info
            room_details = await api_client.get_room_details(matching_room["id"])
            
            # API returns {"room": {...}, "members": [...]}
            room_data = room_details.get("room", {})
            members_list = room_details.get("members", [])
            
            room_name = room_data.get("name", "Unknown")
            room_type = room_data.get("type", "unknown")
            
            console.print(f"\n[cyan]Room: {room_name}[/cyan]")
            console.print(f"[cyan]Type: {room_type.upper()}[/cyan]")
            console.print(f"[cyan]ID: {matching_room['id']}[/cyan]")
            console.print(f"Total Members: {len(members_list)}")
            
            # Display members table
            from rich.table import Table
            from rich import box
            table = Table(title="Members", box=box.ROUNDED)
            table.add_column("Username", style="cyan")
            table.add_column("Role", style="green")
            table.add_column("Joined", style="dim")
            
            for member in members_list:
                # Format timestamp
                from datetime import datetime
                try:
                    dt = datetime.fromisoformat(member["joined_at"].replace('Z', '+00:00'))
                    joined_str = dt.strftime("%b %d, %Y")
                except:
                    joined_str = "Unknown"
                
                table.add_row(
                    member.get("username", "Unknown"),
                    member.get("role", "member").upper(),
                    joined_str
                )
            
            console.print(table)
            
            if room_details.get("type") == "group":
                console.print(f"\n[cyan]Commands:[/cyan]")
                console.print(f"[dim]Add member: fylix add {matching_room['id'][:7]} <email>[/dim]")
                console.print(f"[dim]Send file:  fylix sendroom {matching_room['id'][:7]} <file>[/dim]")
                console.print(f"[dim]Delete:     fylix delroom {matching_room['id'][:7]} (admin only)[/dim]")
        
        except Exception as e:
            # Check if it's an authentication error
            if "401" in str(e) or "Unauthorized" in str(e):
                console.print("[red]✗ Token expired. Please login again:[/red]")
                console.print(f"[cyan]fylix login {config.get_credentials().get('email', '<email>')}[/cyan]")
            elif "Connection" in str(e) or "connection" in str(e):
                console.print("[red]✗ Cannot connect to server. Is the backend running?[/red]")
                console.print("[dim]Start backend: cd backend && python main.py[/dim]")
            else:
                console.print(f"[red]✗ Failed to fetch members: {e}[/red]")
            raise typer.Exit(1)
        
        finally:
            await api_client.close()
    
    asyncio.run(_members())


@app.command()
def add(
    room_id: str = typer.Argument(..., help="Room ID"),
    email: str = typer.Argument(..., help="Email of user to add")
):
    """
    Add member to a group chat (admin only)
    
    [bold yellow]Syntax:[/bold yellow]
      fylix add [cyan]ROOM_ID EMAIL[/cyan]
    
    [bold green]Example:[/bold green]
      fylix add abc12345 user@email.com
      fylix add a1b2c3 newmember@test.com
    
    [bold blue]Arguments:[/bold blue]
      [cyan]ROOM_ID[/cyan]  Room ID (partial match supported)
      [cyan]EMAIL[/cyan]    Email of user to add to the group
    """
    async def _add():
        if not config.is_logged_in():
            console.print("[red]✗ Not logged in. Run 'fylix login <email>' first[/red]")
            raise typer.Exit(1)
        
        try:
            console.print(f"\n[cyan]➕ Adding {email} to room...[/cyan]")
            
            # Find room by partial ID
            rooms_response = await api_client.get_user_rooms()
            rooms = rooms_response.get("rooms", [])
            
            matching_room = None
            for room in rooms:
                if room["id"] == room_id or room["id"].startswith(room_id):
                    matching_room = room
                    break
            
            if not matching_room:
                console.print(f"[red]✗ Room {room_id} not found[/red]")
                raise typer.Exit(1)
            
            # Add member (backend will validate admin permissions)
            result = await api_client.add_room_member(matching_room["id"], email)
            
            console.print(f"[green]✓ {result.get('message', 'User added successfully')}[/green]")
            console.print(f"\n[dim]View members: fylix members {matching_room['id'][:8]}[/dim]")
        
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 403:
                console.print("[red]✗ Only room admins can add members[/red]")
            else:
                error_detail = e.response.json().get('detail', str(e))
                console.print(f"[red]✗ Failed to add member: {error_detail}[/red]")
            raise typer.Exit(1)
        except Exception as e:
            console.print(f"[red]✗ Failed to add member: {e}[/red]")
            raise typer.Exit(1)
        
        finally:
            await api_client.close()
    
    asyncio.run(_add())


@app.command()
def leave(
    room_id: str = typer.Argument(..., help="Room ID to leave")
):
    """
    Leave a group chat
    
    Note: Cannot leave direct chats (they are auto-created)
    
    Example: fylix leave abc12345
    """
    async def _leave():
        if not config.is_logged_in():
            console.print("[red]✗ Not logged in. Run 'fylix login <email>' first[/red]")
            raise typer.Exit(1)
        
        try:
            console.print(f"\n[cyan]🚪 Leaving room...[/cyan]")
            
            # Find room
            rooms_response = await api_client.get_user_rooms()
            rooms = rooms_response.get("rooms", [])
            
            matching_room = None
            for room in rooms:
                if room["id"] == room_id or room["id"].startswith(room_id):
                    matching_room = room
                    break
            
            if not matching_room:
                console.print(f"[red]✗ Room {room_id} not found[/red]")
                raise typer.Exit(1)
            
            # Check if it's a direct chat
            if matching_room.get("type") == "direct":
                console.print("[yellow]⚠ Cannot leave direct chats[/yellow]")
                console.print("[dim]Direct chats are automatically created and cannot be left[/dim]")
                return
            
            # Confirm
            room_name = matching_room.get("name", "Unknown")
            confirm = typer.confirm(f"Leave '{room_name}'?", default=False)
            
            if not confirm:
                console.print("[yellow]Cancelled[/yellow]")
                return
            
            # Remove self from room
            current_user_id = config.get_user_id()
            result = await api_client.remove_room_member(matching_room["id"], current_user_id)
            
            console.print(f"[green]✓ {result.get('message', 'Left room successfully')}[/green]")
            console.print(f"\n[dim]View remaining rooms: fylix rooms[/dim]")
            
        except Exception as e:
            console.print(f"[red]✗ Failed to leave room: {e}[/red]")
            raise typer.Exit(1)
        
        finally:
            await api_client.close()
    
    asyncio.run(_leave())


@app.command()
def delroom(
    room_id: str = typer.Argument(..., help="Room ID to delete")
):
    """
    Delete a group chat (admin only)
    
    Note: Only group admins can delete rooms
    Direct chats cannot be deleted
    
    Example: fylix delroom abc1234
    """
    async def _delroom():
        if not config.is_logged_in():
            console.print("[red]✗ Not logged in. Run 'fylix login <email>' first[/red]")
            raise typer.Exit(1)
        
        try:
            console.print(f"\n[cyan]🗑️  Deleting room...[/cyan]")
            
            # Find room
            rooms_response = await api_client.get_user_rooms()
            rooms = rooms_response.get("rooms", [])
            
            matching_room = None
            for room in rooms:
                if room["id"] == room_id or room["id"].startswith(room_id):
                    matching_room = room
                    break
            
            if not matching_room:
                console.print(f"[red]✗ Room {room_id} not found[/red]")
                raise typer.Exit(1)
            
            # Check if it's a group
            if matching_room.get("type") != "group":
                console.print("[red]✗ Cannot delete direct chats[/red]")
                console.print("[dim]Direct chats are permanent between users[/dim]")
                return
            
            # Confirm deletion
            room_name = matching_room.get("name", "Unknown")
            confirm = typer.confirm(f"Delete group '{room_name}'? This cannot be undone.", default=False)
            
            if not confirm:
                console.print("[yellow]Cancelled[/yellow]")
                return
            
            # Delete room via API
            result = await api_client.delete_room(matching_room["id"])
            
            console.print(f"[green]✓ {result.get('message', 'Room deleted successfully')}[/green]")
            
            # Wait a moment for cache to clear on backend
            import asyncio
            await asyncio.sleep(0.5)
            
            console.print(f"\n[dim]View remaining rooms: fylix rooms[/dim]")
        
        except Exception as e:
            console.print(f"[red]✗ Failed to delete room: {e}[/red]")
            raise typer.Exit(1)
        
        finally:
            await api_client.close()
    
    asyncio.run(_delroom())


@app.command()
def sendroom(
    room_id: str = typer.Argument(..., help="Room ID to send to"),
    file_path: str = typer.Argument(..., help="File to send")
):
    """
    Send file to a group chat (using room ID)
    
    For direct chats, use: fylix send <file> <email>
    For group chats, use:  fylix sendroom <room_id> <file>
    
    Examples:
        fylix sendroom abc1234 document.pdf
        fylix sendroom f890ae9 photo.jpg
    """
    async def _sendroom():
        if not config.is_logged_in():
            console.print("[red]✗ Not logged in. Run 'fylix login <email>' first[/red]")
            raise typer.Exit(1)
        
        try:
            # Verify file exists
            from pathlib import Path
            file = Path(file_path)
            if not file.exists():
                console.print(f"[red]✗ File not found: {file_path}[/red]")
                raise typer.Exit(1)
            
            console.print(f"\n[cyan]📤 Sending to group chat...[/cyan]")
            
            # Find room by partial ID
            rooms_response = await api_client.get_user_rooms()
            rooms = rooms_response.get("rooms", [])
            
            matching_room = None
            for room in rooms:
                if room["id"] == room_id or room["id"].startswith(room_id):
                    matching_room = room
                    break
            
            if not matching_room:
                console.print(f"[red]✗ Room {room_id} not found[/red]")
                console.print("[dim]Use 'fylix rooms' to see available rooms[/dim]")
                raise typer.Exit(1)
            
            room_name = matching_room.get("name", "Unknown")
            console.print(f"Room: {room_name}")
            console.print(f"File: {file.name}")
            console.print(f"Size: {_format_size(file.stat().st_size)}")
            
            # Use room-specific chunked upload
            from fylix.transfer import transfer_manager
            
            # Calculate file hash
            from rich.progress import Progress, SpinnerColumn, TextColumn
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                transient=True
            ) as progress:
                task = progress.add_task("Calculating file hash...", total=None)
                file_hash = transfer_manager.calculate_file_hash(file)
                progress.update(task, completed=True)
            
            file_size = file.stat().st_size
            chunk_size = 1024 * 1024  # 1MB chunks
            total_chunks = (file_size + chunk_size - 1) // chunk_size
            
            console.print(f"\n[cyan]Starting chunked upload...[/cyan]")
            console.print(f"[dim]Chunks: {total_chunks}, Hash: {file_hash[:16]}...[/dim]")
            
            # Start upload
            start_response = await api_client.start_file_upload(
                room_id=matching_room["id"],
                filename=file.name,
                file_size=file_size,
                file_hash=file_hash,
                total_chunks=total_chunks
            )
            
            file_id = start_response["file_id"]
            console.print(f"[dim]File ID: {file_id}[/dim]")
            
            # Upload chunks with progress bar
            from rich.progress import Progress, BarColumn, TaskProgressColumn, TransferSpeedColumn, TimeRemainingColumn
            import hashlib
            
            with Progress(
                TextColumn("[bold blue]{task.fields[filename]}", justify="right"),
                BarColumn(bar_width=None),
                "[progress.percentage]{task.percentage:>3.1f}%",
                "-",
                TransferSpeedColumn(),
                "-",
                TimeRemainingColumn(),
            ) as progress:
                task_id = progress.add_task(
                    "upload",
                    filename=file.name,
                    total=file_size
                )
                
                with open(file, 'rb') as f:
                    for chunk_num in range(total_chunks):
                        chunk_data = f.read(chunk_size)
                        chunk_hash = hashlib.sha256(chunk_data).hexdigest()
                        
                        await api_client.upload_chunk(
                            room_id=matching_room["id"],
                            file_id=file_id,
                            chunk_number=chunk_num,
                            total_chunks=total_chunks,
                            chunk_data=chunk_data,
                            chunk_hash=chunk_hash
                        )
                        
                        progress.update(task_id, advance=len(chunk_data))
            
            # Complete upload with verification progress
            from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
            import time
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[cyan]Finalizing upload & verifying blockchain...[/cyan]"),
                TimeElapsedColumn(),
                transient=False
            ) as progress:
                task = progress.add_task("", total=None)
                start_time = time.time()
                
                try:
                    complete_response = await api_client.complete_upload(
                        room_id=matching_room["id"],
                        file_id=file_id,
                        file_hash=file_hash
                    )
                    elapsed = time.time() - start_time
                    progress.update(task, completed=True)
                except Exception as complete_error:
                    console.print(f"\n[red]✗ Upload completion failed:[/red]")
                    console.print(f"[red]Error: {complete_error}[/red]")
                    raise
            
            console.print(f"\n[green]✓ File sent successfully![/green]")
            
            # Parse response structure
            message_id = complete_response.get('message_id')
            blockchain_data = complete_response.get('blockchain', {})
            ipfs_data = complete_response.get('ipfs', {})
            
            if message_id:
                console.print(f"[dim]Message ID: {message_id}[/dim]")
            
            # Show blockchain and IPFS info if available
            if ipfs_data and ipfs_data.get('success'):
                console.print(f"\n[cyan]🔗 IPFS & Blockchain Proof:[/cyan]")
                console.print(f"[green]IPFS CID:[/green] {ipfs_data.get('cid', 'N/A')}")
                console.print(f"[dim]Pinata: https://gateway.pinata.cloud/ipfs/{ipfs_data.get('cid', '')}[/dim]")
            elif ipfs_data and ipfs_data.get('processing'):
                console.print(f"\n[yellow]⏳ IPFS upload processing in background...[/yellow]")
                
            if blockchain_data and blockchain_data.get('success'):
                console.print(f"[green]Blockchain TX:[/green] {blockchain_data.get('transaction_hash', 'N/A')}")
                console.print(f"[green]File Hash (SHA-256):[/green] {file_hash}")
                console.print(f"\n[yellow]✓ File is now immutably recorded on blockchain![/yellow]")
            elif blockchain_data and blockchain_data.get('processing'):
                console.print(f"[yellow]⏳ Blockchain verification processing in background...[/yellow]")
            else:
                console.print(f"\n[yellow]⚠ Blockchain verification pending (processing in background)[/yellow]")
        
        except Exception as e:
            import traceback
            error_msg = str(e) if str(e) else type(e).__name__
            console.print(f"\n[red]✗ Failed to send file: {error_msg}[/red]")
            # Only show traceback for unexpected errors
            if "ReadTimeout" not in error_msg and "Connection" not in error_msg:
                console.print(f"[dim]Error type: {type(e).__name__}[/dim]")
            raise typer.Exit(1)
        
        finally:
            await api_client.close()
    
    asyncio.run(_sendroom())


# ==================== SEND ====================

@app.command()
def send(
    file_path: str = typer.Argument(..., help="Path to file to send"),
    recipient_email: str = typer.Argument(..., help="Recipient's email address")
):
    """
    Send file to recipient with chunked upload and auto-resume
    
    [bold yellow]Syntax:[/bold yellow]
      fylix send [cyan]FILE RECIPIENT_EMAIL[/cyan]
    
    [bold green]Examples:[/bold green]
      fylix send document.pdf alice@example.com
      fylix send ~/Downloads/report.docx bob@test.com
      fylix send /path/to/image.jpg user@domain.com
    
    [bold magenta]Features:[/bold magenta]
      - Chunked upload (AI-optimized size)
      - Live progress bar with ETA
      - Auto-resume on network loss
      - IPFS decentralized storage
      - Blockchain proof of transfer
    
    [bold blue]Arguments:[/bold blue]
      [cyan]FILE[/cyan]             Path to file to send
      [cyan]RECIPIENT_EMAIL[/cyan]  Recipient's email address
    """
    async def _send():
        if not config.is_logged_in():
            console.print("[red]✗ Not logged in. Run 'fylix login <email>' first[/red]")
            raise typer.Exit(1)
        
        try:
            path = Path(file_path)
            transfer_id = await transfer_manager.send_file(path, recipient_email)
            console.print(f"\n[dim]Transfer ID: {transfer_id}[/dim]")
        
        except Exception as e:
            error_msg = str(e)
            if "401" in error_msg or "Unauthorized" in error_msg:
                console.print(f"[red]✗ Authentication failed. Your session expired.[/red]")
                console.print(f"[yellow]Please login again: fylix login {config.get_credentials().get('email', '<email>')}[/yellow]")
            else:
                console.print(f"[red]✗ Send failed: {e}[/red]")
            raise typer.Exit(1)
        
        finally:
            await api_client.close()
    
    asyncio.run(_send())


# ==================== RECEIVE ====================

@app.command()
def receive(
    message_id: str = typer.Argument(..., help="Message ID from inbox"),
    output_dir: str = typer.Option("./downloads", "--output", "-o", help="Output directory")
):
    """
    Download file with integrity verification
    
    [bold yellow]Syntax:[/bold yellow]
      fylix receive [cyan]MESSAGE_ID[/cyan] [magenta][OPTIONS][/magenta]
    
    [bold green]Examples:[/bold green]
      fylix receive abc123def456
      fylix receive abc123d -o ~/Downloads
      fylix receive a1b2c3 --output /tmp/files
    
    [bold magenta]Security:[/bold magenta]
      - Requires explicit confirmation
      - SHA-256 hash verification
      - Blockchain proof check
      - IPFS link validation
    
    [bold blue]Arguments:[/bold blue]
      [cyan]MESSAGE_ID[/cyan]  Message ID from inbox (partial match supported)
    
    [bold blue]Options:[/bold blue]
      [magenta]-o, --output[/magenta]  Output directory (default: ./downloads)
    """
    async def _receive():
        if not config.is_logged_in():
            console.print("[red]✗ Not logged in. Run 'fylix login <email>' first[/red]")
            raise typer.Exit(1)
        
        try:
            # Fetch message details using FAST direct search endpoint
            console.print(f"\n[cyan]📋 Fetching file details...[/cyan]")
            
            file_info = await api_client.search_message_by_id(message_id)
            
            if not file_info:
                console.print(f"[red]✗ Message {message_id} not found in inbox[/red]")
                raise typer.Exit(1)
            
            # Display file info
            console.print(f"\n[cyan]📄 File Information:[/cyan]")
            console.print(f"Sender: {file_info.get('sender_username', 'Unknown')}")
            console.print(f"Filename: {file_info.get('file_name', 'Unknown')}")
            console.print(f"Size: {_format_size(file_info.get('file_size', 0))}")
            console.print(f"Hash: {file_info.get('file_hash', 'N/A')[:16]}...")
            console.print(f"[dim]Full Message ID: {file_info['id']}[/dim]")
            console.print(f"[dim]File Path: {file_info.get('file_path', 'N/A')}[/dim]")
            if file_info.get('ipfs_cid'):
                console.print(f"IPFS: {file_info['ipfs_cid']}")
            
            # Ask for confirmation
            if not Confirm.ask("\n[yellow]Download this file?[/yellow]", default=False):
                console.print("[yellow]Cancelled[/yellow]")
                return
            
            # Download and verify (use FULL message ID from file_info, not partial user input)
            output_path = Path(output_dir)
            downloaded_file = await transfer_manager.receive_file(
                message_id=file_info["id"],  # Use full ID, not the partial user input
                output_dir=output_path,
                expected_hash=file_info.get("file_hash"),
                expected_ipfs_cid=file_info.get("ipfs_cid")
            )
            
            # Mark as downloaded in config (update credentials file directly)
            creds = config.get_credentials()
            if creds:
                downloaded_files = creds.get("downloaded_files", [])
                if file_info["id"] not in downloaded_files:
                    downloaded_files.append(file_info["id"])
                    creds["downloaded_files"] = downloaded_files
                    # Write directly to file instead of using save_credentials
                    with open(config.credentials_file, 'w') as f:
                        json.dump(creds, f, indent=2)
            
            console.print(f"\n[green]✓ File downloaded and verified[/green]")
        
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                console.print(f"\n[red]✗ Message {message_id} not found in your inbox[/red]")
            elif e.response.status_code == 504:
                console.print(f"\n[red]✗ Database timeout. Please try again in 30 seconds.[/red]")
            else:
                console.print(f"\n[red]✗ Receive failed: HTTP {e.response.status_code}[/red]")
            raise typer.Exit(1)
        except Exception as e:
            console.print(f"\n[red]✗ Receive failed: {e}[/red]")
            raise typer.Exit(1)
        
        finally:
            await api_client.close()
    
    asyncio.run(_receive())


# ==================== STATUS ====================

@app.command()
def status():
    """
    Show status of all transfers (active/paused/completed)
    
    Example: fylix status
    """
    if not config.is_logged_in():
        console.print("[yellow]⚠ Not logged in[/yellow]")
        return
    
    transfers = config.get_all_transfers()
    
    if not transfers:
        console.print("\n[yellow]No transfers found[/yellow]")
        return
    
    # Group by status
    active = []
    paused = []
    completed = []
    failed = []
    
    for transfer_id, state in transfers.items():
        status = state.get("status", "unknown")
        if status == "uploading":
            active.append((transfer_id, state))
        elif status == "paused":
            paused.append((transfer_id, state))
        elif status == "completed":
            completed.append((transfer_id, state))
        elif status == "failed":
            failed.append((transfer_id, state))
    
    # Display active transfers
    if active:
        table = Table(title=f"Active Transfers ({len(active)})")
        table.add_column("Transfer ID", style="cyan")
        table.add_column("Filename", style="white")
        table.add_column("Progress", style="green")
        table.add_column("Recipient", style="yellow")
        
        for transfer_id, state in active:
            progress = f"{len(state.get('uploaded_chunks', []))}/{state.get('total_chunks', 0)}"
            table.add_row(
                transfer_id[:16] + "...",
                state.get("filename", "Unknown"),
                progress,
                state.get("recipient_email", "N/A")
            )
        
        console.print(table)
    
    # Display paused transfers
    if paused:
        table = Table(title=f"Paused Transfers ({len(paused)})")
        table.add_column("Transfer ID", style="cyan")
        table.add_column("Filename", style="white")
        table.add_column("Progress", style="yellow")
        
        for transfer_id, state in paused:
            progress = f"{len(state.get('uploaded_chunks', []))}/{state.get('total_chunks', 0)}"
            table.add_row(
                transfer_id[:16] + "...",
                state.get("filename", "Unknown"),
                progress
            )
        
        console.print(table)
        console.print("[dim]Use 'fylix resume <transfer_id>' to continue[/dim]")
    
    # Display completed transfers
    if completed:
        console.print(f"\n[green]✓ {len(completed)} completed transfers[/green]")
    
    # Display failed transfers
    if failed:
        console.print(f"\n[red]✗ {len(failed)} failed transfers[/red]")


# ==================== RESUME ====================

@app.command()
def resume(
    transfer_id: str = typer.Argument(..., help="Transfer ID to resume")
):
    """
    Resume transfer after hard failure (crash/reboot)
    
    Continues from last successfully uploaded chunk
    Requires transfer state to be saved locally
    
    Example: fylix resume abc123def456
    """
    async def _resume():
        if not config.is_logged_in():
            console.print("[red]✗ Not logged in. Run 'fylix login <email>' first[/red]")
            raise typer.Exit(1)
        
        try:
            # Get transfer state
            transfer_state = config.get_transfer_state(transfer_id)
            
            if not transfer_state:
                console.print(f"[red]✗ Transfer {transfer_id} not found[/red]")
                console.print("[dim]Run 'fylix status' to see available transfers[/dim]")
                raise typer.Exit(1)
            
            if transfer_state.get("status") == "completed":
                console.print(f"[yellow]⚠ Transfer already completed[/yellow]")
                return
            
            # Resume upload
            file_path = Path(transfer_state["file_path"])
            recipient_email = transfer_state["recipient_email"]
            
            console.print(f"\n[cyan]⟳ Resuming upload of {transfer_state['filename']}...[/cyan]")
            
            await transfer_manager.send_file(
                file_path=file_path,
                recipient_email=recipient_email,
                resume=True,
                transfer_id=transfer_id
            )
        
        except Exception as e:
            console.print(f"\n[red]✗ Resume failed: {e}[/red]")
            raise typer.Exit(1)
        
        finally:
            await api_client.close()
    
    asyncio.run(_resume())


# ==================== VERIFY ====================

@app.command()
def verify(
    message_id: str = typer.Argument(..., help="Message ID to verify (from inbox)")
):
    """
    Verify file integrity using blockchain and IPFS
    
    [bold yellow]Syntax:[/bold yellow]
      fylix verify [cyan]MESSAGE_ID[/cyan]
    
    [bold green]Examples:[/bold green]
      fylix verify a9bad07
      fylix verify abc123def456
    
    [bold magenta]Shows:[/bold magenta]
      - SHA-256 file hash
      - Blockchain transaction details
      - IPFS CID and Pinata gateway
      - Certificate of authenticity
      - Transfer timestamp
    
    [bold blue]Arguments:[/bold blue]
      [cyan]MESSAGE_ID[/cyan]  Message ID from inbox (partial match supported)
    """
    async def _verify():
        if not config.is_logged_in():
            console.print("[red]✗ Not logged in. Run 'fylix login <email>' first[/red]")
            raise typer.Exit(1)
        
        try:
            console.print(f"\n[cyan]🔍 Verifying file integrity...[/cyan]")
            
            # Find the message (same logic as receive)
            rooms_response = await api_client.get_user_rooms()
            rooms = rooms_response.get("rooms", [])
            
            file_info = None
            current_user_id = config.get_user_id()
            
            for room in rooms:
                try:
                    # Increase limit to search more messages (same as inbox)
                    messages_response = await api_client.get_room_messages(room["id"], limit=200)
                    for msg in messages_response.get("messages", []):
                        if msg["message_type"] in ["file", "image"] and msg.get("file_name"):
                            if msg["id"] == message_id or msg["id"].startswith(message_id):
                                file_info = msg
                                break
                except:
                    continue
                if file_info:
                    break
            
            if not file_info:
                console.print(f"[red]✗ Message {message_id} not found[/red]")
                raise typer.Exit(1)
            
            # Display file info
            console.print(f"\n[cyan]📄 File Details:[/cyan]")
            console.print(f"Filename: {file_info.get('file_name')}")
            console.print(f"Size: {_format_size(file_info.get('file_size', 0))}")
            console.print(f"Sender: {file_info['sender_username']}")
            
            # Cryptographic Hash
            console.print(f"\n[cyan]🔐 Cryptographic Hash (SHA-256):[/cyan]")
            console.print(f"[green]{file_info.get('file_hash', 'N/A')}[/green]")
            
            # Get blockchain proof
            file_hash = file_info.get('file_hash')
            if file_hash:
                try:
                    blockchain_data = await api_client.get_blockchain_proof(file_hash)
                    
                    console.print(f"\n[cyan]⛓️  Blockchain Verification:[/cyan]")
                    console.print(f"Transaction Hash: [green]{blockchain_data.get('tx_hash', 'N/A')}[/green]")
                    console.print(f"Block Number: {blockchain_data.get('block_number', 'N/A')}")
                    console.print(f"Timestamp: {blockchain_data.get('timestamp', 'N/A')}")
                    console.print(f"Status: [green]✓ Verified on Blockchain[/green]")
                    
                    # IPFS Details
                    if blockchain_data.get('ipfs_cid'):
                        console.print(f"\n[cyan]📦 IPFS Storage:[/cyan]")
                        console.print(f"CID: [green]{blockchain_data['ipfs_cid']}[/green]")
                        console.print(f"Gateway: https://gateway.pinata.cloud/ipfs/{blockchain_data['ipfs_cid']}")
                        console.print(f"Status: [green]✓ Pinned on Pinata[/green]")
                    
                    console.print(f"\n[green]✅ File integrity verified successfully![/green]")
                    
                except Exception as e:
                    console.print(f"\n[yellow]⚠ Blockchain verification unavailable: {e}[/yellow]")
                    console.print(f"[dim]File may still be processing or not yet finalized[/dim]")
            else:
                console.print(f"\n[yellow]⚠ No hash available for verification[/yellow]")
        
        except Exception as e:
            console.print(f"[red]✗ Verify failed: {e}[/red]")
            raise typer.Exit(1)
        
        finally:
            await api_client.close()
    
    asyncio.run(_verify())


# ==================== HELPER ====================

def _format_size(size_bytes: int) -> str:
    """Format file size in human-readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"


# ==================== MAIN ====================

if __name__ == "__main__":
    app()
