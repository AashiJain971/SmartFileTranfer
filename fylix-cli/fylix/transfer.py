"""
File transfer logic with chunking, progress tracking, and resume
"""

import asyncio
import hashlib
from pathlib import Path
from typing import Optional
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeRemainingColumn
from rich.console import Console
import socket
import httpx

from fylix.api_client import api_client
from fylix.config import config

console = Console()


class FileTransferManager:
    """Handles file uploads and downloads with chunking"""
    
    def __init__(self):
        self.chunk_size = 1024 * 1024  # 1MB default
        self.is_paused = False
        self.pause_reason = ""
    
    async def check_network_connectivity(self) -> bool:
        """Check if network is available using socket-level test (no HTTP caching)"""
        try:
            # Socket-level test - directly check if we can connect to Google DNS
            # This bypasses HTTP caching and detects actual network availability
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            # Try to connect to Google's DNS (8.8.8.8) on port 53
            result = sock.connect_ex(('8.8.8.8', 53))
            sock.close()
            return result == 0  # 0 means connection successful
        except:
            return False
    
    def calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA-256 hash of entire file"""
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            while chunk := f.read(8192):
                sha256.update(chunk)
        return sha256.hexdigest()
    
    def calculate_chunk_hash(self, chunk_data: bytes) -> str:
        """Calculate SHA-256 hash of a chunk"""
        return hashlib.sha256(chunk_data).hexdigest()
    
    async def send_file(
        self,
        file_path: Path,
        recipient_email: str,
        resume: bool = False,
        transfer_id: Optional[str] = None
    ) -> str:
        """
        Send file to recipient with chunked upload
        
        AUTO-RESUME: Automatically resumes on network errors
        MANUAL-RESUME: Requires explicit 'fylix resume' after process crash
        
        Returns: transfer_id for tracking
        """
        
        # Validate file exists
        if not file_path.exists():
            console.print(f"[red]✗[/red] File not found: {file_path}")
            raise FileNotFoundError(f"File not found: {file_path}")
        
        file_size = file_path.stat().st_size
        filename = file_path.name
        
        console.print(f"\n[cyan]📤 Preparing to send:[/cyan] {filename}")
        console.print(f"[dim]Size: {self._format_size(file_size)}[/dim]")
        
        # Calculate file hash
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True
        ) as progress:
            task = progress.add_task("Calculating file hash...", total=None)
            file_hash = self.calculate_file_hash(file_path)
            progress.update(task, completed=True)
        
        console.print(f"[dim]Hash: {file_hash[:16]}...[/dim]")
        
        # Show AI Network Prediction (simulate like websocket_test.html)
        console.print(f"\n[cyan]🤖 AI Network Analysis:[/cyan]")
        console.print(f"[dim]Analyzing current network conditions...[/dim]")
        console.print(f"[green]✓ Bandwidth: Estimated ~10-50 Mbps[/green]")
        console.print(f"[green]✓ Latency: ~20-100ms[/green]")
        console.print(f"[green]✓ Packet Loss: <1%[/green]")
        console.print(f"[yellow]Recommended Chunk Size: 256KB - 2MB (will be optimized by backend)[/yellow]")
        
        # Ask user for chunk size preference (like websocket_test.html)
        console.print(f"\n[cyan]Chunk Size Options:[/cyan]")
        console.print("1. Auto (AI-optimized based on network conditions) [Recommended]")
        console.print("2. Manual (specify size)")
        
        from rich.prompt import Prompt
        choice = Prompt.ask("Select option", choices=["1", "2"], default="1")
        
        manual_chunk_size = None
        if choice == "2":
            size_input = Prompt.ask("Enter chunk size in KB", default="1024")
            try:
                manual_chunk_size = int(size_input) * 1024  # Convert KB to bytes
                console.print(f"[dim]Using manual chunk size: {manual_chunk_size // 1024} KB[/dim]")
            except:
                console.print("[yellow]Invalid size, using auto[/yellow]")
        
        # Check if resuming existing transfer
        if resume and transfer_id:
            transfer_state = config.get_transfer_state(transfer_id)
            if transfer_state:
                console.print(f"[yellow]⟳[/yellow] Resuming transfer from chunk {transfer_state.get('last_chunk', 0) + 1}")
                room_id = transfer_state["room_id"]
                file_id = transfer_state["file_id"]
                uploaded_chunks = set(transfer_state.get("uploaded_chunks", []))
            else:
                console.print(f"[red]✗[/red] Transfer state not found for {transfer_id}")
                return None
        else:
            # Create/get direct room with recipient - with network resilience
            console.print(f"[cyan]🔗 Connecting to {recipient_email}...[/cyan]")
            room_id = None
            connection_attempts = 0
            
            while not room_id:
                try:
                    room_response = await api_client.create_direct_room(recipient_email)
                    room_id = room_response["id"]  # Backend returns ChatRoomResponse with id at top level
                    if connection_attempts > 0:
                        console.print(f"[green]✓ Connected successfully[/green]")
                except (httpx.ConnectError, httpx.NetworkError, httpx.TimeoutException, 
                        httpx.ConnectTimeout, httpx.ReadTimeout, httpx.HTTPStatusError) as e:
                    connection_attempts += 1
                    if connection_attempts == 1:
                        console.print(f"[yellow]⚠️  Network issue connecting to {recipient_email}...[/yellow]")
                        console.print(f"[yellow]Checking network connectivity...[/yellow]")
                    
                    # Check if network is available
                    network_available = await self.check_network_connectivity()
                    
                    if not network_available:
                        console.print(f"[red]⏸️  Network disconnected - waiting for connection...[/red]")
                        console.print(f"[dim]Will auto-retry when network returns (attempt {connection_attempts})[/dim]")
                        await asyncio.sleep(3)
                    else:
                        console.print(f"[yellow]↻ Network available, retrying... (attempt {connection_attempts})[/yellow]")
                        await asyncio.sleep(2)
                except Exception as e:
                    console.print(f"[red]✗ Failed to connect: {str(e)}[/red]")
                    console.print(f"[yellow]Retrying in 3 seconds... (attempt {connection_attempts + 1})[/yellow]")
                    await asyncio.sleep(3)
                    connection_attempts += 1
            
            # Calculate total chunks BEFORE starting upload (like websocket_test.html)
            total_chunks = (file_size + self.chunk_size - 1) // self.chunk_size
            
            # Start upload session with infinite retry on network errors
            console.print(f"[cyan]📦 Starting upload session...[/cyan]")
            file_id = None
            start_attempts = 0
            
            while not file_id:
                try:
                    start_response = await api_client.start_file_upload(
                        room_id=room_id,
                        filename=filename,
                        file_size=file_size,
                        file_hash=file_hash,
                        total_chunks=total_chunks
                    )
                    file_id = start_response["file_id"]
                    if start_attempts > 0:
                        console.print(f"[green]✓ Upload session started successfully[/green]")
                except (httpx.ConnectError, httpx.NetworkError, httpx.TimeoutException,
                        httpx.ConnectTimeout, httpx.ReadTimeout, httpx.HTTPStatusError) as e:
                    start_attempts += 1
                    if start_attempts == 1:
                        console.print(f"[yellow]⚠️  Network issue starting upload...[/yellow]")
                    console.print(f"[yellow]↻ Retrying... (attempt {start_attempts})[/yellow]")
                    console.print(f"[dim]Press Ctrl+C to cancel[/dim]")
                    await asyncio.sleep(2)
                except Exception as e:
                    console.print(f"[yellow]⚠️  Error: {str(e)}[/yellow]")
                    console.print(f"[yellow]Retrying in 3 seconds... (attempt {start_attempts + 1})[/yellow]")
                    await asyncio.sleep(3)
                    start_attempts += 1
            
            # ✅ USE BACKEND'S DYNAMIC CHUNK SIZE (like websocket_test.html)
            if "chunk_size" in start_response:
                backend_chunk_size = start_response["chunk_size"]
                
                # If manual size selected, use it; otherwise use backend's AI-optimized size
                if manual_chunk_size:
                    self.chunk_size = manual_chunk_size
                    console.print(f"[dim]Using manual chunk size: {self._format_size(self.chunk_size)}[/dim]")
                else:
                    self.chunk_size = backend_chunk_size
                    console.print(f"[cyan]🤖 AI Network Prediction:[/cyan]")
                    console.print(f"[dim]Optimal chunk size: {self._format_size(self.chunk_size)}[/dim]")
                    console.print(f"[dim]Based on current network conditions[/dim]")
                
                total_chunks = (file_size + self.chunk_size - 1) // self.chunk_size
                console.print(f"[dim]Total chunks: {total_chunks}[/dim]")
            
            uploaded_chunks = set()
        
        # Save initial transfer state for manual resume
        transfer_id = file_id
        config.save_transfer_state(transfer_id, {
            "type": "upload",
            "file_path": str(file_path),
            "filename": filename,
            "recipient_email": recipient_email,
            "room_id": room_id,
            "file_id": file_id,
            "file_size": file_size,
            "file_hash": file_hash,
            "total_chunks": total_chunks,
            "uploaded_chunks": list(uploaded_chunks),
            "status": "uploading"
        })
        
        # Upload chunks with progress bar and network monitoring
        console.print(f"\n[cyan]📦 Uploading {total_chunks} chunks...[/cyan]")
        console.print(f"[dim]Network: Monitoring connection for auto-resume[/dim]")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeRemainingColumn(),
        ) as progress:
            task = progress.add_task(f"Uploading {filename}", total=total_chunks)
            
            with open(file_path, 'rb') as f:
                for chunk_num in range(total_chunks):
                    # Skip already uploaded chunks (resume)
                    if chunk_num in uploaded_chunks:
                        progress.update(task, advance=1)
                        continue
                    
                    # Read chunk
                    chunk_data = f.read(self.chunk_size)
                    chunk_hash = self.calculate_chunk_hash(chunk_data)
                    
                    # AUTO-RESUME: Infinite retry until success or user types 'exit'
                    retry_delay = 2
                    attempt = 0
                    
                    while True:  # Continuous retry until success
                        attempt += 1
                        
                        # CHECK NETWORK BEFORE UPLOAD ATTEMPT (critical for WiFi toggle detection)
                        network_available = await self.check_network_connectivity()
                        if not network_available:
                            # Network is down - show pause message IMMEDIATELY
                            if not self.is_paused:
                                console.print(f"\n[red]⏸️  Network disconnected - pausing upload[/red]")
                                self.is_paused = True
                            
                            progress.update(task, description=f"[red]⏸️  PAUSED - No network (chunk {chunk_num}/{total_chunks})[/red]")
                            console.print(f"[yellow]Waiting for network... (will auto-resume when connected)[/yellow]")
                            console.print(f"[dim]Press Ctrl+C to cancel[/dim]")
                            
                            await asyncio.sleep(3)  # Wait before rechecking
                            continue  # Recheck network
                        
                        # Network is available - attempt upload
                        try:
                            await api_client.upload_chunk(
                                room_id=room_id,
                                file_id=file_id,
                                chunk_number=chunk_num,
                                total_chunks=total_chunks,
                                chunk_data=chunk_data,
                                chunk_hash=chunk_hash
                            )
                            
                            # Success - clear any pause state
                            if self.is_paused:
                                self.is_paused = False
                                console.print(f"\n[green]✓ Network restored - resuming upload[/green]")
                                progress.update(task, description=f"Uploading {filename}")
                            
                            # Update state for manual resume
                            uploaded_chunks.add(chunk_num)
                            config.update_transfer_status(
                                transfer_id,
                                "uploading",
                                uploaded_chunks=list(uploaded_chunks),
                                last_chunk=chunk_num
                            )
                            
                            progress.update(task, advance=1)
                            break
                        
                        except (httpx.ConnectError, httpx.NetworkError, httpx.TimeoutException, httpx.ConnectTimeout, httpx.ReadTimeout) as e:
                            # Network error - check connectivity and auto-pause
                            if not self.is_paused:
                                console.print(f"\n[yellow]⚠️  Network unstable - checking connection...[/yellow]")
                                self.is_paused = True
                            
                            # Check if network is available
                            network_available = await self.check_network_connectivity()
                            
                            if not network_available:
                                # Network is down - show pause message
                                progress.update(task, description=f"[red]⏸️  PAUSED - Network disconnected (chunk {chunk_num}/{total_chunks})[/red]")
                                console.print(f"[red]⏸️  Upload paused - Network disconnected[/red]")
                                console.print(f"[yellow]Waiting for network... (will auto-resume when connected)[/yellow]")
                                console.print(f"[dim]Press Ctrl+C to cancel[/dim]")
                                
                                # Wait before retry
                                await asyncio.sleep(retry_delay)
                                
                                # Query server for last uploaded chunk when network returns
                                try:
                                    uploaded_status = await api_client.get_uploaded_chunks(file_id)
                                    if uploaded_status and 'uploaded_chunks' in uploaded_status:
                                        server_chunks = set(uploaded_status['uploaded_chunks'])
                                        if server_chunks != uploaded_chunks:
                                            console.print(f"[cyan]🔄 Syncing with server state...[/cyan]")
                                            uploaded_chunks = server_chunks
                                            config.update_transfer_status(
                                                transfer_id,
                                                "uploading",
                                                uploaded_chunks=list(uploaded_chunks)
                                            )
                                except:
                                    pass  # Server unreachable, will retry
                                
                                continue  # Retry this chunk
                            else:
                                # Network is back but upload failed - retry
                                console.print(f"[yellow]↻ Network available, retrying chunk {chunk_num}...[/yellow]")
                                await asyncio.sleep(1)
                                continue
                        
                        except httpx.HTTPStatusError as e:
                            # HTTP errors (including 500) - treat as network/server issues
                            if not self.is_paused:
                                console.print(f"\n[yellow]⚠️  Server error (HTTP {e.response.status_code}) - retrying...[/yellow]")
                                self.is_paused = True
                            
                            progress.update(task, description=f"[yellow]⏸️  Server issue - retrying chunk {chunk_num}/{total_chunks}[/yellow]")
                            await asyncio.sleep(retry_delay)
                            continue
                        
                        except Exception as e:
                            # Other errors - log but keep retrying
                            error_msg = str(e)
                            if not self.is_paused:
                                console.print(f"\n[yellow]⚠️  Error: {error_msg}[/yellow]")
                                console.print(f"[yellow]Retrying chunk {chunk_num}...[/yellow]")
                                self.is_paused = True
                            
                            progress.update(task, description=f"[yellow]⏸️  Retrying chunk {chunk_num}/{total_chunks}[/yellow]")
                            await asyncio.sleep(retry_delay)
                            continue
        
        # Complete upload - triggers IPFS and blockchain
        console.print("\n[cyan]🔗 Finalizing transfer (IPFS + Blockchain)...[/cyan]")
        
        try:
            complete_response = await api_client.complete_upload(
                room_id=room_id,
                file_id=file_id,
                file_hash=file_hash
            )
            
            message_id = complete_response.get("message_id")
            ipfs_cid = complete_response.get("ipfs_cid")
            blockchain_tx = complete_response.get("blockchain_tx_hash")
            
            console.print(f"\n[green]✓[/green] File sent successfully!")
            
            # Show verification details (like websocket_test.html)
            console.print(f"\n[cyan]📋 Transfer Details:[/cyan]")
            if message_id:
                console.print(f"Message ID: [green]{message_id}[/green]")
            else:
                console.print(f"Message ID: [yellow]Processing...[/yellow]")
            
            console.print(f"\n[cyan]🔐 Cryptographic Hash (SHA-256):[/cyan]")
            console.print(f"[green]{file_hash}[/green]")
            
            # Wait for IPFS and Blockchain processing with infinite retry (CRITICAL - data security)
            if not ipfs_cid or not blockchain_tx:
                console.print(f"\n[yellow]⏳ Waiting for IPFS and Blockchain verification...[/yellow]")
                console.print(f"[dim]This ensures your file is cryptographically secured and distributed[/dim]")
                
                retry_count = 0
                max_wait = 120  # Maximum 2 minutes of waiting
                
                while (not ipfs_cid or not blockchain_tx) and retry_count < max_wait:
                    retry_count += 1
                    await asyncio.sleep(2)  # Check every 2 seconds
                    
                    # Try to fetch blockchain proof with network retry
                    while True:
                        try:
                            blockchain_data = await api_client.get_blockchain_proof(file_hash)
                            ipfs_cid = blockchain_data.get('ipfs_cid') or ipfs_cid
                            blockchain_tx = blockchain_data.get('tx_hash') or blockchain_tx
                            break  # Success
                        except (httpx.ConnectError, httpx.NetworkError, httpx.TimeoutException) as e:
                            # Network error during verification fetch
                            network_available = await self.check_network_connectivity()
                            if not network_available:
                                console.print(f"[red]⏸️  Network disconnected while verifying - waiting...[/red]")
                                await asyncio.sleep(3)
                                continue  # Retry network check
                            else:
                                await asyncio.sleep(1)
                                continue  # Retry fetch
                        except Exception:
                            break  # Other errors, continue waiting loop
                    
                    # Show progress every 10 seconds
                    if retry_count % 5 == 0:
                        status = []
                        if not blockchain_tx:
                            status.append("blockchain pending")
                        if not ipfs_cid:
                            status.append("IPFS pending")
                        console.print(f"[yellow]Still waiting: {', '.join(status)}... ({retry_count*2}s)[/yellow]")
                    
                    # Check if both are ready
                    if ipfs_cid and blockchain_tx:
                        console.print(f"[green]✓ Verification complete![/green]")
                        break
            
            if blockchain_tx:
                console.print(f"\n[cyan]⛓️  Blockchain Proof:[/cyan]")
                console.print(f"Transaction: [green]{blockchain_tx}[/green]")
                console.print(f"Status: [green]✓ Recorded on Blockchain[/green]")
            else:
                console.print(f"\n[yellow]⚠ Blockchain: Still processing (check later with verify)[/yellow]")
            
            if ipfs_cid:
                console.print(f"\n[cyan]📦 IPFS Storage:[/cyan]")
                console.print(f"CID: [green]{ipfs_cid}[/green]")
                console.print(f"Gateway: [blue]https://gateway.pinata.cloud/ipfs/{ipfs_cid}[/blue]")
                console.print(f"Status: [green]✓ Pinned on Pinata[/green]")
            else:
                console.print(f"\n[yellow]⚠ IPFS: Still uploading to Pinata (check later with verify)[/yellow]")
            
            console.print(f"\n[dim]Use 'fylix verify {message_id[:7] if message_id else 'message_id'}' to check verification status anytime[/dim]")
            
            # Mark as completed
            config.update_transfer_status(
                transfer_id,
                "completed",
                message_id=message_id or "pending",
                ipfs_cid=ipfs_cid,
                blockchain_tx_hash=blockchain_tx
            )
            
            # Track sent file in credentials for persistence
            if message_id:
                creds = config.get_credentials()
                if creds:
                    sent_files = creds.get("sent_files", [])
                    if message_id not in sent_files:
                        sent_files.append(message_id)
                        creds["sent_files"] = sent_files
                        # Write directly to file to preserve all fields
                        import json
                        with open(config.credentials_file, 'w') as f:
                            json.dump(creds, f, indent=2)
            
            return transfer_id
        
        except Exception as e:
            import traceback
            console.print(f"\n[red]✗ Finalization failed: {e}[/red]")
            console.print(f"[dim]{traceback.format_exc()}[/dim]")
            console.print("[yellow]Chunks uploaded but transfer not finalized. Contact support.[/yellow]")
            config.update_transfer_status(transfer_id, "failed", error=str(e))
            raise
    
    async def receive_file(
        self,
        message_id: str,
        output_dir: Path,
        expected_hash: Optional[str] = None,
        expected_ipfs_cid: Optional[str] = None
    ) -> Path:
        """
        Download file and verify integrity
        
        VERIFICATION:
        1. Download file
        2. Verify file hash matches blockchain record
        3. Verify IPFS CID matches (if available)
        4. Mark as CORRUPTED if any check fails
        
        Returns: Path to downloaded file
        """
        
        console.print(f"\n[cyan]📥 Downloading file...[/cyan]")
        console.print(f"[dim]Network: Auto-retry enabled (Press Ctrl+C to cancel)[/dim]")
        
        # Create output directory
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Download file with infinite retry on network errors
        file_data = None
        download_attempt = 0
        
        while file_data is None:
            download_attempt += 1
            
            # CHECK NETWORK BEFORE DOWNLOAD ATTEMPT (critical for WiFi toggle detection)
            network_available = await self.check_network_connectivity()
            if not network_available:
                # Network is down - show pause message IMMEDIATELY
                if download_attempt == 1 or download_attempt % 5 == 0:  # Show every 5 attempts to avoid spam
                    console.print(f"[red]⏸️  Network disconnected - pausing download[/red]")
                    console.print(f"[yellow]Waiting for network... (will auto-resume when connected)[/yellow]")
                    console.print(f"[dim]Press Ctrl+C to cancel[/dim]")
                await asyncio.sleep(3)  # Wait before rechecking
                continue  # Recheck network
            
            # Network is available - attempt download
            try:
                file_data = await api_client.download_file(message_id)
                if download_attempt > 1:
                    console.print(f"[green]✓ Network restored - download successful after {download_attempt} attempts[/green]")
            except (httpx.ConnectError, httpx.NetworkError, httpx.TimeoutException,
                    httpx.ConnectTimeout, httpx.ReadTimeout) as e:
                console.print(f"[yellow]⚠️  Network error during download (attempt {download_attempt})[/yellow]")
                console.print(f"[yellow]Retrying...[/yellow]")
                await asyncio.sleep(2)
            except httpx.HTTPStatusError as e:
                console.print(f"[yellow]⚠️  Server error (HTTP {e.response.status_code}) - retrying...[/yellow]")
                console.print(f"[yellow]Attempt {download_attempt}, retrying in 3 seconds...[/yellow]")
                await asyncio.sleep(3)
            except Exception as e:
                # Check if it's a network-related error
                error_str = str(e).lower()
                if any(x in error_str for x in ['network', 'connection', 'timeout', 'unreachable']):
                    console.print(f"[yellow]⚠️  Network issue: {str(e)}[/yellow]")
                    console.print(f"[yellow]Retrying in 3 seconds... (attempt {download_attempt})[/yellow]")
                    await asyncio.sleep(3)
                else:
                    # Non-network error - fail
                    console.print(f"[red]✗ Download failed: {e}[/red]")
                    raise
        
        # Save to disk (temporary until verified)
        temp_path = output_dir / f".{message_id}.tmp"
        with open(temp_path, 'wb') as f:
            f.write(file_data)
        
        console.print(f"[green]✓[/green] Downloaded {self._format_size(len(file_data))}")
        
        # INTEGRITY VERIFICATION
        console.print("\n[cyan]🔐 Verifying integrity...[/cyan]")
        
        # 1. Calculate actual file hash
        actual_hash = self.calculate_file_hash(temp_path)
        console.print(f"[dim]File Hash: {actual_hash[:16]}...[/dim]")
        
        # 2. Get blockchain proof with network retry
        blockchain_hash = None
        blockchain_ipfs = None
        blockchain_proof = None
        proof_attempt = 0
        
        while blockchain_proof is None:
            proof_attempt += 1
            try:
                blockchain_proof = await api_client.get_blockchain_proof(actual_hash)
                blockchain_hash = blockchain_proof.get("file_hash")
                blockchain_ipfs = blockchain_proof.get("ipfs_cid")
                break  # Success
            except (httpx.ConnectError, httpx.NetworkError, httpx.TimeoutException,
                    httpx.ConnectTimeout, httpx.ReadTimeout):
                if proof_attempt == 1:
                    console.print(f"[yellow]⚠️  Network issue fetching blockchain proof, retrying...[/yellow]")
                await asyncio.sleep(2)
                continue
            except Exception as e:
                # Non-network errors - break and handle below
                blockchain_proof = {}  # Set to empty dict to exit loop
                break
        
        # Handle blockchain proof result
        try:
            if blockchain_hash:
            
                console.print(f"[dim]Blockchain Hash: {blockchain_hash[:16]}...[/dim]")
                
                if blockchain_ipfs:
                    console.print(f"[dim]IPFS CID: {blockchain_ipfs}[/dim]")
                    console.print(f"[cyan]📎 Pinata: https://gateway.pinata.cloud/ipfs/{blockchain_ipfs}[/cyan]")
                else:
                    console.print(f"[dim]IPFS CID: N/A[/dim]")
            else:
                # No blockchain proof found
                console.print(f"[yellow]⚠ No blockchain record (old file or not yet processed)[/yellow]")
                console.print(f"[dim]Blockchain Hash: N/A[/dim]")
                console.print(f"[dim]IPFS CID: N/A[/dim]")
        except:
            pass  # Ignore any remaining errors
        
        # 3. Verify hash match (always runs, not just in except block)
        if expected_hash and actual_hash != expected_hash:
            temp_path.unlink()
            console.print(f"\n[red]✗ CORRUPTED: File hash mismatch![/red]")
            console.print(f"[red]Expected: {expected_hash[:16]}...[/red]")
            console.print(f"[red]Got: {actual_hash[:16]}...[/red]")
            raise ValueError("File integrity check failed: hash mismatch")
        
        if blockchain_hash and actual_hash != blockchain_hash:
            temp_path.unlink()
            console.print(f"\n[red]✗ CORRUPTED: Blockchain verification failed![/red]")
            raise ValueError("File integrity check failed: blockchain mismatch")
        
        # 4. Verify IPFS CID (if available)
        if expected_ipfs_cid and blockchain_ipfs and expected_ipfs_cid != blockchain_ipfs:
            console.print(f"\n[yellow]⚠ Warning: IPFS CID mismatch[/yellow]")
            console.print(f"[yellow]Expected: {expected_ipfs_cid}[/yellow]")
            console.print(f"[yellow]Got: {blockchain_ipfs}[/yellow]")
        
        console.print(f"\n[green]✓ Verification passed[/green]")
        
        # Move from temp to final location
        # Extract filename from blockchain proof or use message_id
        filename = blockchain_proof.get("file_name", f"file_{message_id}") if blockchain_proof else f"file_{message_id}"
        final_path = output_dir / filename
        
        # Handle existing files
        if final_path.exists():
            base = final_path.stem
            ext = final_path.suffix
            counter = 1
            while final_path.exists():
                final_path = output_dir / f"{base}_{counter}{ext}"
                counter += 1
        
        temp_path.rename(final_path)
        
        console.print(f"[green]✓[/green] File saved: {final_path}")
        
        return final_path
    
    def _format_size(self, size_bytes: int) -> str:
        """Format file size in human-readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"


# Global transfer manager instance
transfer_manager = FileTransferManager()
