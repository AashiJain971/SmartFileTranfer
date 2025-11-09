"""
Certificate Generation Service
Creates PDF certificates with blockchain proof and QR codes
"""

from reportlab.lib.pagesizes import letter, A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from reportlab.lib.colors import HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import qrcode
from io import BytesIO
from datetime import datetime
from typing import Dict, Any, Optional
import os

class CertificateService:
    """Service for generating blockchain proof certificates"""
    
    def __init__(self):
        """Initialize certificate service"""
        self.page_width, self.page_height = letter
        self.margin = 0.75 * inch
        
        # Colors
        self.primary_color = HexColor('#25d366')  # WhatsApp green
        self.dark_color = HexColor('#075e54')
        self.light_gray = HexColor('#ece5dd')
        self.text_color = HexColor('#000000')
    
    def generate_blockchain_certificate(
        self,
        file_info: Dict[str, Any],
        blockchain_info: Dict[str, Any],
        ipfs_info: Optional[Dict[str, Any]] = None
    ) -> bytes:
        """
        Generate PDF certificate with blockchain proof
        
        Args:
            file_info: File metadata (name, size, hash, etc.)
            blockchain_info: Blockchain transaction details
            ipfs_info: Optional IPFS upload details
            
        Returns:
            bytes: PDF certificate data
        """
        buffer = BytesIO()
        pdf = canvas.Canvas(buffer, pagesize=letter)
        
        # Title section
        self._draw_header(pdf)
        
        # Certificate content
        y_position = self.page_height - 2.5 * inch
        
        # File Information
        y_position = self._draw_section(
            pdf, 
            "📄 File Information", 
            y_position,
            [
                ("File Name", file_info.get('name', 'N/A')),
                ("File Size", self._format_file_size(file_info.get('size', 0))),
                ("SHA-256 Hash", file_info.get('hash', 'N/A')),
                ("Upload Date", file_info.get('timestamp', datetime.now().isoformat()))
            ]
        )
        
        # Transfer Details
        y_position = self._draw_section(
            pdf,
            "👥 Transfer Details",
            y_position - 0.5 * inch,
            [
                ("Sender", file_info.get('sender_id', 'N/A')),
                ("Receiver", file_info.get('receiver_id', 'N/A')),
                ("Room ID", file_info.get('room_id', 'N/A'))
            ]
        )
        
        # Blockchain Proof
        if blockchain_info and blockchain_info.get('success'):
            y_position = self._draw_section(
                pdf,
                "🔗 Blockchain Verification",
                y_position - 0.5 * inch,
                [
                    ("Network", "Ethereum Sepolia Testnet"),
                    ("Transaction Hash", blockchain_info.get('transaction_hash', 'N/A')),
                    ("Block Number", str(blockchain_info.get('block_number', 'N/A'))),
                    ("Gas Used", str(blockchain_info.get('gas_used', 'N/A'))),
                    ("Confirmation Time", blockchain_info.get('timestamp', 'N/A')),
                    ("Contract Address", blockchain_info.get('contract_address', 'N/A'))
                ]
            )
            
            # QR Code for Etherscan link
            if blockchain_info.get('explorer_url'):
                self._draw_qr_code(
                    pdf,
                    blockchain_info['explorer_url'],
                    x=self.page_width - 2.5 * inch,
                    y=y_position - 1.5 * inch,
                    size=1.5 * inch,
                    label="Verify on Etherscan"
                )
        
        # IPFS Information (if available)
        if ipfs_info and ipfs_info.get('success'):
            y_position = self._draw_section(
                pdf,
                "🌐 IPFS Decentralized Storage",
                y_position - 0.5 * inch,
                [
                    ("IPFS CID", ipfs_info.get('cid', 'N/A')),
                    ("Gateway URL", ipfs_info.get('primary_url', 'N/A')[:60] + '...')
                ]
            )
            
            # QR Code for IPFS gateway
            if ipfs_info.get('primary_url'):
                self._draw_qr_code(
                    pdf,
                    ipfs_info['primary_url'],
                    x=self.margin,
                    y=y_position - 1.5 * inch,
                    size=1.5 * inch,
                    label="Download from IPFS"
                )
        
        # Footer
        self._draw_footer(pdf)
        
        # Save PDF
        pdf.save()
        buffer.seek(0)
        return buffer.getvalue()
    
    def _draw_header(self, pdf: canvas.Canvas):
        """Draw certificate header"""
        # Background rectangle
        pdf.setFillColor(self.dark_color)
        pdf.rect(0, self.page_height - 1.5 * inch, self.page_width, 1.5 * inch, fill=True, stroke=False)
        
        # Title
        pdf.setFillColor(HexColor('#FFFFFF'))
        pdf.setFont("Helvetica-Bold", 24)
        pdf.drawCentredString(
            self.page_width / 2,
            self.page_height - 0.9 * inch,
            "🔗 BLOCKCHAIN TRANSFER CERTIFICATE"
        )
        
        # Subtitle
        pdf.setFont("Helvetica", 12)
        pdf.drawCentredString(
            self.page_width / 2,
            self.page_height - 1.2 * inch,
            "Cryptographically Verified File Transfer Proof"
        )
    
    def _draw_section(
        self,
        pdf: canvas.Canvas,
        title: str,
        y_position: float,
        items: list
    ) -> float:
        """Draw a section with title and key-value pairs"""
        # Section title
        pdf.setFillColor(self.dark_color)
        pdf.setFont("Helvetica-Bold", 14)
        pdf.drawString(self.margin, y_position, title)
        
        y_position -= 0.3 * inch
        
        # Items
        pdf.setFillColor(self.text_color)
        pdf.setFont("Helvetica", 10)
        
        for label, value in items:
            # Label
            pdf.setFont("Helvetica-Bold", 10)
            pdf.drawString(self.margin + 0.2 * inch, y_position, f"{label}:")
            
            # Value
            pdf.setFont("Courier", 9)
            value_str = str(value)
            
            # Wrap long values
            if len(value_str) > 80:
                value_str = value_str[:80] + "..."
            
            pdf.drawString(self.margin + 2.0 * inch, y_position, value_str)
            
            y_position -= 0.25 * inch
        
        return y_position
    
    def _draw_qr_code(
        self,
        pdf: canvas.Canvas,
        data: str,
        x: float,
        y: float,
        size: float,
        label: str = ""
    ):
        """Draw QR code"""
        # Generate QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=4
        )
        qr.add_data(data)
        qr.make(fit=True)
        
        qr_img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to bytes
        qr_buffer = BytesIO()
        qr_img.save(qr_buffer, format='PNG')
        qr_buffer.seek(0)
        
        # Draw QR code
        pdf.drawImage(
            ImageReader(qr_buffer),
            x, y,
            width=size,
            height=size,
            preserveAspectRatio=True
        )
        
        # Draw label
        if label:
            pdf.setFont("Helvetica", 9)
            pdf.setFillColor(self.text_color)
            pdf.drawCentredString(x + size / 2, y - 0.2 * inch, label)
    
    def _draw_footer(self, pdf: canvas.Canvas):
        """Draw certificate footer"""
        y_position = self.margin
        
        pdf.setFont("Helvetica-Italic", 9)
        pdf.setFillColor(HexColor('#666666'))
        
        footer_text = [
            "This certificate is cryptographically verifiable on the Ethereum blockchain.",
            "The file hash and transfer details are permanently recorded and cannot be altered.",
            "Scan the QR codes to verify the blockchain transaction and access the file on IPFS.",
            f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}"
        ]
        
        for text in footer_text:
            pdf.drawCentredString(self.page_width / 2, y_position, text)
            y_position += 0.15 * inch
    
    @staticmethod
    def _format_file_size(size_bytes: int) -> str:
        """Format file size in human-readable format"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} PB"


# Singleton instance
_certificate_service = None

def get_certificate_service() -> CertificateService:
    """Get singleton certificate service instance"""
    global _certificate_service
    if _certificate_service is None:
        _certificate_service = CertificateService()
    return _certificate_service
