"use client";

import { AnimatePresence, motion } from "motion/react";
import { LogOut, Menu, Network, X } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import type { ReactNode } from "react";
import { useState } from "react";

import { cn } from "@/lib/cn";
import { useAuthStore } from "@/stores/auth-store";

export interface NavItem {
  href: string;
  label: string;
  icon: ReactNode;
  /** Treat descendant routes as active too (e.g. /properties/{id}). */
  matchPrefix?: boolean;
}

interface AppShellProps {
  nav: NavItem[];
  /** Shown under the product name — which workspace the user is in. */
  roleLabel: string;
  children: ReactNode;
}

export function AppShell({ nav, roleLabel, children }: AppShellProps) {
  const pathname = usePathname();
  const router = useRouter();
  const email = useAuthStore((state) => state.email);
  const signOut = useAuthStore((state) => state.signOut);
  const [menuOpen, setMenuOpen] = useState(false);

  const isActive = (item: NavItem) =>
    item.matchPrefix ? pathname.startsWith(item.href) : pathname === item.href;

  const handleSignOut = () => {
    signOut();
    router.replace("/login");
  };

  const navList = (
    <nav className="flex flex-col gap-1" aria-label="Main">
      {nav.map((item) => {
        const active = isActive(item);
        return (
          <Link
            key={item.href}
            href={item.href}
            // Navigating on mobile should put the drawer away. Handled on the
            // event rather than in an effect watching the pathname.
            onClick={() => setMenuOpen(false)}
            aria-current={active ? "page" : undefined}
            className={cn(
              "relative flex items-center gap-3 rounded-card px-3 py-2.5 text-sm",
              active
                ? "bg-shell-hover font-medium text-white"
                : "text-white/70 hover:bg-shell-hover hover:text-white",
            )}
          >
            {active ? (
              <motion.span
                layoutId="nav-indicator"
                className="absolute top-1/2 left-0 h-6 w-[3px] -translate-y-1/2 rounded-full bg-brand"
                transition={{ duration: 0.25, ease: "easeOut" }}
              />
            ) : null}
            <span className="shrink-0">{item.icon}</span>
            {item.label}
          </Link>
        );
      })}
    </nav>
  );

  const brand = (
    <div className="flex items-center gap-2.5">
      <span className="flex h-9 w-9 items-center justify-center rounded-card bg-brand text-white">
        <Network size={18} />
      </span>
      <span className="leading-tight">
        <span className="block text-sm font-bold text-white">Dispatcher</span>
        <span className="block text-xs text-white/60">{roleLabel}</span>
      </span>
    </div>
  );

  const account = (
    <div className="border-t border-white/10 pt-4">
      {email ? (
        <p className="truncate px-3 pb-2 text-xs text-white/60" title={email}>
          {email}
        </p>
      ) : null}
      <button
        type="button"
        onClick={handleSignOut}
        className="flex w-full items-center gap-3 rounded-card px-3 py-2.5 text-sm text-white/70 hover:bg-shell-hover hover:text-white"
      >
        <LogOut size={18} />
        Sign out
      </button>
    </div>
  );

  return (
    <div className="flex min-h-[100dvh] flex-col md:flex-row">
      {/* Mobile bar */}
      <header className="sticky top-0 z-[100] flex items-center justify-between gap-3 bg-shell px-4 py-3 md:hidden">
        {brand}
        <button
          type="button"
          onClick={() => setMenuOpen(true)}
          aria-label="Open menu"
          className="rounded-card p-2 text-white/80 hover:bg-shell-hover hover:text-white"
        >
          <Menu size={20} />
        </button>
      </header>

      {/* Desktop sidebar */}
      <aside className="sticky top-0 hidden h-[100dvh] w-64 shrink-0 flex-col justify-between bg-shell px-4 py-6 md:flex">
        <div className="flex flex-col gap-8">
          {brand}
          {navList}
        </div>
        {account}
      </aside>

      {/* Mobile drawer */}
      <AnimatePresence>
        {menuOpen ? (
          <div className="fixed inset-0 z-[300] md:hidden">
            <motion.div
              className="absolute inset-0 z-[200] bg-shell-strong/50"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2, ease: "easeOut" }}
              onClick={() => setMenuOpen(false)}
              aria-hidden
            />
            <motion.div
              className="relative z-[300] flex h-full w-72 max-w-[85%] flex-col justify-between bg-shell px-4 py-6"
              initial={{ x: -288 }}
              animate={{ x: 0 }}
              exit={{ x: -288 }}
              transition={{ duration: 0.25, ease: "easeOut" }}
            >
              <div className="flex flex-col gap-8">
                <div className="flex items-center justify-between">
                  {brand}
                  <button
                    type="button"
                    onClick={() => setMenuOpen(false)}
                    aria-label="Close menu"
                    className="rounded p-1 text-white/70 hover:text-white"
                  >
                    <X size={18} />
                  </button>
                </div>
                {navList}
              </div>
              {account}
            </motion.div>
          </div>
        ) : null}
      </AnimatePresence>

      <main className="min-w-0 flex-1">
        <div className="mx-auto w-full max-w-[1280px] px-6 py-8 md:py-10">
          {children}
        </div>
      </main>
    </div>
  );
}
