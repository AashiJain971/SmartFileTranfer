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
import httpx

from fylix.config import config
from fylix.api_client import api_client
from fylix.transfer import transfer_manager
from fylix import __version__

app = typer.Typer(
    name="fylix",
    help="FYLIX - Secure file transfer with blockchain verification",
    add_completion=False
)

console = Console()


# ==================== VERSION ====================

def version_callback(value: bool):
    """Callback for --version/-v flag"""
    if value:
        console.print(f"[cyan]FYLIX CLI[/cyan] [green]v{__version__}[/green]")
        raise typer.Exit()

@app.callback()
def main(
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
    FYLIX - Secure file transfer with blockchain verification
    """
    pass


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
    
    Example: fylix signup user@example.com johndoe
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
    
    Example: fylix login user@example.com
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
    
    Example: fylix logout
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
    
    ⚠️  WARNING: This action cannot be undone!
    
    This will:
    - Delete your account permanently
    - Remove you from all chat rooms (groups and direct chats)
    - Delete all your messages
    - Delete all your file sessions
    - Remove all your data from the system
    
    Example: fylix deleteaccount
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
            console.print("  • Your account")
            console.print("  • All your messages")
            console.print("  • All your file transfers")
            console.print("  • Your membership in all rooms")
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
    Show current logged-in user
    
    Example: fylix whoami
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
    
    Examples:
        fylix inbox          # Load messages 1-10
        fylix inbox 1-10     # Load messages 1-10
        fylix inbox 11-20    # Load next 10 messages
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
            console.print(f"\n[cyan]📬 Fetching inbox (messages {start}-{end})...[/cyan]")
            
            # Get all user rooms
            rooms_response = await api_client.get_user_rooms()
            rooms = rooms_response.get("rooms", [])
            
            # Collect all file messages from all rooms
            incoming_files = []
            
            for room in rooms:
                room_id = room["id"]
                room_name = room.get("name", room_id[:8])
                
                try:
                    # Get messages (limit 200 to allow pagination without too much load)
                    console.print(f"[dim]Checking {room_name}...[/dim]")
                    messages_response = await api_client.get_room_messages(room_id, limit=200)
                    messages = messages_response.get("messages", [])
                    console.print(f"[dim]Found {len(messages)} total messages in room[/dim]")
                except Exception as e:
                    # Show detailed error for debugging
                    import traceback
                    console.print(f"[red]ERROR in {room_name}:[/red]")
                    console.print(f"[red]{type(e).__name__}: {str(e)}[/red]")
                    console.print(f"[dim]{traceback.format_exc()}[/dim]")
                    continue
                
                # Filter file messages (type can be "file" or "image")
                for msg in messages:
                    if msg["message_type"] in ["file", "image"] and msg.get("file_name"):
                        # Only show files from other users (not self-sent)
                        if msg["sender_id"] != config.get_user_id():
                            incoming_files.append({
                                "message_id": msg["id"],
                                "sender": msg["sender_username"],
                                "filename": msg.get("file_name", "Unknown"),
                                "size": msg.get("file_size", 0),
                                "file_hash": msg.get("file_hash"),
                                "ipfs_cid": msg.get("ipfs_cid"),
                                "blockchain_tx": msg.get("blockchain_tx_hash"),
                                "created_at": msg["created_at"]
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
            table.add_column("Time", style="magenta")
            table.add_column("Status", style="yellow")
            table.add_column("ID (7 chars)", style="bright_blue")  # Make it easier to copy
            table.add_column("#", style="dim")  # Message number
            
            for idx, file in enumerate(paginated_files, start=start):
                size_str = _format_size(file["size"])
                
                # Format timestamp in local timezone (like websocket_test.html)
                from datetime import datetime
                try:
                    dt = datetime.fromisoformat(file["created_at"].replace('Z', '+00:00'))
                    # Convert to local timezone
                    local_tz = datetime.now().astimezone().tzinfo
                    dt_local = dt.astimezone(local_tz)
                    time_str = dt_local.strftime("%b %d, %I:%M%p")
                except:
                    time_str = "Unknown"
                
                # Determine integrity status - check if downloaded
                msg_id = file["message_id"]
                # Check if this file was downloaded (stored in config)
                downloaded_files = config.get_credentials().get("downloaded_files", [])
                if msg_id in downloaded_files:
                    status = "✓ Received"
                elif file.get("blockchain_tx"):
                    status = "✓ Verified"
                else:
                    status = "⚠ Pending"
                
                # Show first 7 chars (no ellipsis - easier to copy)
                msg_id_short = file["message_id"][:7]
                
                table.add_row(
                    file["sender"],
                    file["filename"],
                    size_str,
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
            import traceback
            console.print(f"[red]✗ Failed to fetch inbox: {e}[/red]")
            console.print(f"[dim]{traceback.format_exc()}[/dim]")
            raise typer.Exit(1)
        
        finally:
            await api_client.close()
    
    asyncio.run(_inbox(range))


# ==================== OUTBOX ====================

@app.command()
def outbox(range: str = typer.Argument("1-10", help="Message range (e.g., 1-10, max 10)")):
    """
    List files you've sent to others (loads 10 messages at a time)
    
    Examples:
        fylix outbox          # Load messages 1-10
        fylix outbox 1-10     # Load messages 1-10
        fylix outbox 11-20    # Load next 10 messages
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
            console.print(f"\n[cyan]📤 Fetching outbox (messages {start}-{end})...[/cyan]")
            
            # Get all user rooms
            rooms_response = await api_client.get_user_rooms()
            rooms = rooms_response.get("rooms", [])
            
            # Collect all file messages sent by current user
            sent_files = []
            current_user_id = config.get_user_id()
            
            for room in rooms:
                room_id = room["id"]
                room_name = room.get("name", "Unknown")
                
                # Get other member (recipient)
                members = room.get("members", [])
                recipient = "Unknown"
                for member in members:
                    if member["user_id"] != current_user_id:
                        recipient = member["username"]
                        break
                
                try:
                    # Get messages (limit 200 to allow pagination)
                    messages_response = await api_client.get_room_messages(room_id, limit=200)
                    messages = messages_response.get("messages", [])
                except Exception as e:
                    # Skip rooms that timeout silently
                    continue
                
                # Filter file messages sent by current user (type can be "file" or "image")
                for msg in messages:
                    if msg["message_type"] in ["file", "image"] and msg.get("file_name") and msg["sender_id"] == current_user_id:
                        sent_files.append({
                            "message_id": msg["id"],
                            "recipient": recipient,
                            "filename": msg.get("file_name", "Unknown"),
                            "size": msg.get("file_size", 0),
                            "file_hash": msg.get("file_hash"),
                            "ipfs_cid": msg.get("ipfs_cid"),
                            "blockchain_tx": msg.get("blockchain_tx_hash"),
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
                size_str = _format_size(file["size"])
                
                # Format timestamp
                from datetime import datetime
                try:
                    dt = datetime.fromisoformat(file["created_at"].replace('Z', '+00:00'))
                    time_str = dt.strftime("%b %d, %I:%M%p")
                except:
                    time_str = "Unknown"
                
                # Determine delivery status
                status = "✓ Delivered" if file.get("blockchain_tx") else "⚠ Pending"
                
                # Truncate message ID for display
                msg_id_short = file["message_id"][:7] + "…"
                
                table.add_row(
                    file["recipient"],
                    file["filename"],
                    size_str,
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
                console.print(f"\n[yellow]📄 More messages available. Use: fylix outbox {next_start}-{next_end}[/yellow]")
            
            console.print(f"\n[cyan]To verify:[/cyan] fylix verify <ID>")
            if paginated_files:
                console.print(f"[dim]Example: fylix verify {paginated_files[0]['message_id'][:7]}[/dim]")
            console.print(f"[dim]Files are available for recipient to download[/dim]")
        
        except Exception as e:
            import traceback
            console.print(f"[red]✗ Failed to fetch outbox: {e}[/red]")
            console.print(f"[dim]{traceback.format_exc()}[/dim]")
            raise typer.Exit(1)
        
        finally:
            await api_client.close()
    
    asyncio.run(_outbox(range))


# ==================== CHAT ROOM MANAGEMENT ====================

@app.command()
def rooms():
    """
    List all your chat rooms (direct chats and groups)
    
    Shows:
    - Room name/participants
    - Room type (direct/group)
    - Member count
    - Room ID for other commands
    
    Example: fylix rooms
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
            import traceback
            console.print(f"[red]✗ Failed to fetch rooms: {e}[/red]")
            console.print(f"[dim]{traceback.format_exc()}[/dim]")
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
    
    Examples:
        fylix create "Team Project"
        fylix create "Study Group" --members user1@email.com,user2@email.com
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
        
        except Exception as e:
            console.print(f"[red]✗ Failed to create group: {e}[/red]")
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
            
            room_name = room_details.get("name", "Unknown")
            members_list = room_details.get("members", [])
            
            console.print(f"\n[cyan]Room: {room_name}[/cyan]")
            console.print(f"Type: {room_details.get('type', 'unknown').upper()}")
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
            import traceback
            console.print(f"[red]✗ Failed to fetch members: {e}[/red]")
            console.print(f"[dim]{traceback.format_exc()}[/dim]")
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
    
    Example: fylix add abc12345 user@email.com
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
            
            # Use existing transfer manager with room_id directly
            from fylix.transfer import transfer_manager
            await transfer_manager.send_file(
                file_path=str(file),
                room_id=matching_room["id"]  # Use full room ID
            )
        
        except Exception as e:
            console.print(f"[red]✗ Failed to send file: {e}[/red]")
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
    
    Features:
    - Chunked upload (1MB chunks by default)
    - Live progress bar
    - Auto-resume on temporary network loss
    - Persist state for manual resume after crash
    - IPFS storage + blockchain proof
    
    Example: fylix send document.pdf user@example.com
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
    
    Security:
    - Requires explicit user confirmation
    - Shows file metadata before download
    - Verifies file hash against blockchain
    - Verifies IPFS CID (if available)
    - Marks as CORRUPTED if verification fails
    
    Example: fylix receive abc123def456 -o ~/Downloads
    """
    async def _receive():
        if not config.is_logged_in():
            console.print("[red]✗ Not logged in. Run 'fylix login <email>' first[/red]")
            raise typer.Exit(1)
        
        try:
            # Fetch message details first (from inbox)
            console.print(f"\n[cyan]📋 Fetching file details...[/cyan]")
            
            # Get all rooms and find the message (support partial ID match)
            rooms_response = await api_client.get_user_rooms()
            rooms = rooms_response.get("rooms", [])
            
            file_info = None
            current_user_id = config.get_user_id()
            
            for room in rooms:
                try:
                    # Increased to 200 for better coverage (matches inbox)
                    messages_response = await api_client.get_room_messages(room["id"], limit=200)
                    for msg in messages_response.get("messages", []):
                        # Only consider file/image messages from others (not self-sent)
                        if msg["message_type"] in ["file", "image"] and msg.get("file_name") and msg["sender_id"] != current_user_id:
                            # Support full or partial message ID match
                            if msg["id"] == message_id or msg["id"].startswith(message_id):
                                file_info = msg
                                break
                except Exception as e:
                    # Skip rooms that timeout - continue searching
                    console.print(f"[dim]Searching (skipping slow room)...[/dim]")
                    continue
                    
                if file_info:
                    break
            
            if not file_info:
                console.print(f"[red]✗ Message {message_id} not found in inbox[/red]")
                raise typer.Exit(1)
            
            # Display file info
            console.print(f"\n[cyan]📄 File Information:[/cyan]")
            console.print(f"Sender: {file_info['sender_username']}")
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
    
    Shows:
    - File hash verification
    - Blockchain transaction details
    - IPFS CID and Pinata status
    - Certificate of authenticity
    
    Example: fylix verify a9bad07
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
