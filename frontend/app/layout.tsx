import type { Metadata } from 'next';
import './globals.css';
export const metadata: Metadata = {title:'R.A.E. | Control Plane', description:'Workflow registry, governance controls, and execution audit.'};
export default function RootLayout({children}: {children: React.ReactNode}) {return <html lang="en"><body>{children}</body></html>}
