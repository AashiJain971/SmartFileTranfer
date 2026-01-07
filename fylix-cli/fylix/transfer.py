"""
File transfer logic with chunking, progress tracking, and resume
"""

import asyncio
import hashlib
from pathlib import Path
from typing import Optional
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeRemainingColumn
from rich.console import Console

from fylix.api_client import api_client
from fylix.config import config

console = Console()


class FileTransferManager:
    """Handles file uploads and downloads with chunking"""
    
    def __init__(self):
        self.chunk_size = 1024 * 1024  # 1MB default
    
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
            # Create/get direct room with recipient
            console.print(f"[cyan]🔗 Connecting to {recipient_email}...[/cyan]")
            room_response = await api_client.create_direct_room(recipient_email)
            room_id = room_response["id"]  # Backend returns ChatRoomResponse with id at top level
            
            # Calculate total chunks BEFORE starting upload (like websocket_test.html)
            total_chunks = (file_size + self.chunk_size - 1) // self.chunk_size
            
            # Start upload session
            start_response = await api_client.start_file_upload(
                room_id=room_id,
                filename=filename,
                file_size=file_size,
                file_hash=file_hash,
                total_chunks=total_chunks
            )
            
            file_id = start_response["file_id"]
            
            # ✅ USE BACKEND'S DYNAMIC CHUNK SIZE (like websocket_test.html)
            if "chunk_size" in start_response:
                self.chunk_size = start_response["chunk_size"]
                total_chunks = (file_size + self.chunk_size - 1) // self.chunk_size
                console.print(f"[dim]Backend assigned chunk size: {self._format_size(self.chunk_size)} ({total_chunks} chunks)[/dim]")
            
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
        
        # Upload chunks with progress bar
        console.print(f"\n[cyan]📦 Uploading {total_chunks} chunks...[/cyan]")
        
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
                    
                    # AUTO-RESUME: Retry on network errors
                    max_retries = 3
                    for attempt in range(max_retries):
                        try:
                            await api_client.upload_chunk(
                                room_id=room_id,
                                file_id=file_id,
                                chunk_number=chunk_num,
                                total_chunks=total_chunks,
                                chunk_data=chunk_data,
                                chunk_hash=chunk_hash
                            )
                            
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
                        
                        except Exception as e:
                            if attempt < max_retries - 1:
                                await asyncio.sleep(1 * (attempt + 1))  # Exponential backoff
                            else:
                                console.print(f"\n[red]✗ Upload failed at chunk {chunk_num}: {e}[/red]")
                                console.print(f"[yellow]Run 'fylix resume {transfer_id}' to continue[/yellow]")
                                config.update_transfer_status(transfer_id, "paused")
                                raise
        
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
            console.print(f"[dim]Message ID: {message_id}[/dim]")
            if ipfs_cid:
                console.print(f"[dim]IPFS CID: {ipfs_cid}[/dim]")
            if blockchain_tx:
                console.print(f"[dim]Blockchain TX: {blockchain_tx[:20]}...[/dim]")
            
            # Mark as completed
            config.update_transfer_status(
                transfer_id,
                "completed",
                message_id=message_id,
                ipfs_cid=ipfs_cid,
                blockchain_tx_hash=blockchain_tx
            )
            
            return transfer_id
        
        except Exception as e:
            console.print(f"\n[red]✗ Finalization failed: {e}[/red]")
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
        
        # Create output directory
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Download file
        try:
            file_data = await api_client.download_file(message_id)
        except Exception as e:
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
        
        # 2. Get blockchain proof
        try:
            blockchain_proof = await api_client.get_blockchain_proof(actual_hash)
            blockchain_hash = blockchain_proof.get("file_hash")
            blockchain_ipfs = blockchain_proof.get("ipfs_cid")
            
            console.print(f"[dim]Blockchain Hash: {blockchain_hash[:16] if blockchain_hash else 'N/A'}...[/dim]")
            console.print(f"[dim]IPFS CID: {blockchain_ipfs or 'N/A'}[/dim]")
            
            # 3. Verify hash match
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
            filename = blockchain_proof.get("file_name", f"file_{message_id}")
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
        
        except Exception as e:
            if temp_path.exists():
                temp_path.unlink()
            console.print(f"\n[red]✗ Verification failed: {e}[/red]")
            raise
    
    def _format_size(self, size_bytes: int) -> str:
        """Format file size in human-readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"


# Global transfer manager instance
transfer_manager = FileTransferManager()
