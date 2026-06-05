import './globals.css';
import type { Metadata } from 'next';
import { EB_Garamond, IBM_Plex_Mono } from 'next/font/google';
import { Nav } from '../components/nav';
import { Footer } from '../components/footer';
import { StageSwitcher } from '../components/stage-switcher';
import { SvgFilters } from '../components/svg-filters';
import { CommandPalette } from '../components/command-palette';

const display = EB_Garamond({
  subsets: ['latin'],
  style: ['normal', 'italic'],
  weight: ['400', '500', '600', '700'],
  variable: '--font-display-loaded',
  display: 'swap',
});

const mono = IBM_Plex_Mono({
  subsets: ['latin'],
  weight: ['300', '400', '500', '600', '700'],
  variable: '--font-mono-loaded',
  display: 'swap',
});

export const metadata: Metadata = {
  title: 'HackRitual',
  description:
    'A portable, single-container event platform for ritualised collaborative invention. Summon. Forge. Dispel.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="en"
      data-theme="hacker-solarpunk"
      className={`${display.variable} ${mono.variable}`}
    >
      <body className="min-h-screen flex flex-col">
        <SvgFilters />
        <StageSwitcher />
        <Nav />
        <main className="flex-1">{children}</main>
        <Footer />
        <CommandPalette />
      </body>
    </html>
  );
}
