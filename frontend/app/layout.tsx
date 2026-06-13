import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import { MsalProvider } from '@/components/providers/MsalProvider';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'R.A.E. Control Plane - Enterprise AI Governance',
  description: 'NIST AI RMF-aligned governance and control plane for enterprise AI systems with PHI/PII compliance.',
  keywords: 'AI governance, NIST AI RMF, R.A.E., control plane, compliance, HIPAA, SOC 2',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <meta charSet="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <link rel="icon" href="/favicon.ico" />
      </head>
      <body className={inter.className}>
        {/* Microsoft Entra ID (Azure AD) Authentication Provider */}
        <MsalProvider>
          <div className="min-h-screen bg-gray-50">
            {children}
          </div>
        </MsalProvider>
      </body>
    </html>
  );
}
