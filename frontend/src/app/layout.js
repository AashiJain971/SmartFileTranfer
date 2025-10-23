import "./globals.css";
import ClientLayout from '../components/ClientLayout';

export const metadata = {
  title: "Smart File Transfer",
  description: "Secure file upload and download system with real-time progress tracking",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body className="antialiased">
        <ClientLayout>
          {children}
        </ClientLayout>
      </body>
    </html>
  );
}
