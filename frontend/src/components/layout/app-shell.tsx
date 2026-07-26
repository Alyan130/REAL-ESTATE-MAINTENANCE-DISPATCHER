"use client";

import { AnimatePresence, motion } from "motion/react";
import { ChevronLeft, ChevronRight, LogOut, Menu, Network, X } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import type { ReactNode } from "react";
import { useEffect, useState } from "react";

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
  const [collapsed, setCollapsed] = useState(false);

  useEffect(() => {
    const saved = localStorage.getItem("sidebar_collapsed");
    if (saved !== null) {
      setCollapsed(saved === "true");
    }
  }, []);

  const toggleSidebar = () => {
    setCollapsed((prev) => {
      const next = !prev;
      localStorage.setItem("sidebar_collapsed", String(next));
      return next;
    });
  };

  const isActive = (item: NavItem) =>
    item.matchPrefix ? pathname.startsWith(item.href) : pathname === item.href;

  const handleSignOut = () => {
    signOut();
    router.replace("/login");
  };

  const renderNavList = (isMobile = false) => (
    <nav className="flex flex-col gap-1.5" aria-label="Main">
      {nav.map((item) => {
        const active = isActive(item);
        const isCollapsedMode = collapsed && !isMobile;

        return (
          <Link
            key={item.href}
            href={item.href}
            onClick={() => setMenuOpen(false)}
            aria-current={active ? "page" : undefined}
            title={isCollapsedMode ? item.label : undefined}
            className={cn(
              "relative flex items-center rounded-full transition-all duration-200 text-sm font-medium",
              isCollapsedMode
                ? "h-11 w-11 justify-center mx-auto px-0"
                : "gap-3 px-4 py-2.5",
              active
                ? "bg-brand-soft text-brand font-semibold"
                : "text-muted hover:bg-sunken hover:text-ink-strong",
            )}
          >
            {active ? (
              <motion.span
                layoutId="nav-indicator"
                className={cn(
                  "absolute rounded-full bg-brand",
                  isCollapsedMode
                    ? "top-1/2 left-0.5 h-4 w-1 -translate-y-1/2"
                    : "top-1/2 left-1.5 h-4 w-1 -translate-y-1/2",
                )}
                transition={{ duration: 0.25, ease: "easeOut" }}
              />
            ) : null}
            <span className="shrink-0">{item.icon}</span>
            {!isCollapsedMode && (
              <span className="truncate">{item.label}</span>
            )}
          </Link>
        );
      })}
    </nav>
  );

  const brandMobile = (
    <div className="flex items-center gap-3">
      <span className="flex h-9 w-9 items-center justify-center rounded-full bg-brand text-white shadow-[0_2px_8px_rgba(0,117,222,0.3)] shrink-0">
        <Network size={18} />
      </span>
      <span className="leading-tight">
        <span className="block text-sm font-bold text-ink-strong tracking-tight">
          Dispatcher
        </span>
        <span className="block text-xs font-medium text-muted">{roleLabel}</span>
      </span>
    </div>
  );

  return (
    <div className="flex min-h-[100dvh] flex-col md:flex-row bg-canvas">
      {/* Mobile bar */}
      <header className="sticky top-0 z-[100] flex items-center justify-between gap-3 border-b border-line-soft bg-shell/95 backdrop-blur-md px-4 py-3 md:hidden">
        {brandMobile}
        <button
          type="button"
          onClick={() => setMenuOpen(true)}
          aria-label="Open menu"
          className="rounded-full p-2 text-muted hover:bg-sunken hover:text-ink-strong cursor-pointer"
        >
          <Menu size={20} />
        </button>
      </header>

      {/* Desktop sidebar */}
      <aside
        className={cn(
          "sticky top-0 hidden h-[100dvh] shrink-0 flex-col border-r border-line-soft bg-shell py-5 transition-all duration-300 ease-in-out md:flex",
          collapsed ? "w-20 px-2" : "w-64 px-4",
        )}
      >
        {/* Header */}
        <div
          className={cn(
            "flex items-center pb-4 border-b border-line-soft/60 shrink-0",
            collapsed ? "justify-center flex-col gap-3" : "justify-between gap-2 px-1",
          )}
        >
          <div className="flex items-center gap-3 overflow-hidden">
            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-brand text-white shadow-[0_2px_8px_rgba(0,117,222,0.3)]">
              <Network size={18} />
            </span>
            {!collapsed && (
              <span className="leading-tight whitespace-nowrap overflow-hidden transition-all duration-300">
                <span className="block text-sm font-bold text-ink-strong tracking-tight">
                  Dispatcher
                </span>
                <span className="block text-xs font-medium text-muted">{roleLabel}</span>
              </span>
            )}
          </div>
          <button
            type="button"
            onClick={toggleSidebar}
            title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            className="flex h-8 w-8 items-center justify-center rounded-full text-muted hover:bg-sunken hover:text-ink-strong transition-colors shrink-0 cursor-pointer"
          >
            {collapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
          </button>
        </div>

        {/* Scrollable Navigation Area */}
        <div className="flex-1 min-h-0 overflow-y-auto overflow-x-hidden py-4 space-y-1">
          {renderNavList(false)}
        </div>

        {/* Footer Account Section */}
        <div
          className={cn(
            "border-t border-line-soft/80 pt-3 shrink-0",
            collapsed ? "flex flex-col items-center" : "",
          )}
        >
          {email && !collapsed ? (
            <p className="truncate px-4 pb-2 text-xs font-mono text-muted" title={email}>
              {email}
            </p>
          ) : null}
          <button
            type="button"
            onClick={handleSignOut}
            title={collapsed ? `Sign out (${email ?? ""})` : undefined}
            className={cn(
              "flex items-center rounded-full transition-colors text-sm font-medium text-muted hover:bg-danger-soft hover:text-danger cursor-pointer",
              collapsed
                ? "h-11 w-11 justify-center mx-auto px-0"
                : "w-full gap-3 px-4 py-2.5",
            )}
          >
            <LogOut size={18} className="shrink-0" />
            {!collapsed && <span>Sign out</span>}
          </button>
        </div>
      </aside>

      {/* Mobile drawer */}
      <AnimatePresence>
        {menuOpen ? (
          <div className="fixed inset-0 z-[300] md:hidden">
            <motion.div
              className="absolute inset-0 z-[200] bg-shell-strong/40 backdrop-blur-xs"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2, ease: "easeOut" }}
              onClick={() => setMenuOpen(false)}
              aria-hidden
            />
            <motion.div
              className="relative z-[300] flex h-full w-72 max-w-[85%] flex-col justify-between border-r border-line-soft bg-shell px-4 py-6 shadow-overlay"
              initial={{ x: -288 }}
              animate={{ x: 0 }}
              exit={{ x: -288 }}
              transition={{ duration: 0.25, ease: "easeOut" }}
            >
              <div className="flex flex-col gap-6">
                <div className="flex items-center justify-between">
                  {brandMobile}
                  <button
                    type="button"
                    onClick={() => setMenuOpen(false)}
                    aria-label="Close menu"
                    className="rounded-full p-1.5 text-muted hover:bg-sunken hover:text-ink-strong cursor-pointer"
                  >
                    <X size={18} />
                  </button>
                </div>
                <div className="flex-1 overflow-y-auto">
                  {renderNavList(true)}
                </div>
              </div>

              <div className="border-t border-line-soft/80 pt-4">
                {email ? (
                  <p className="truncate px-4 pb-2 text-xs font-mono text-muted" title={email}>
                    {email}
                  </p>
                ) : null}
                <button
                  type="button"
                  onClick={handleSignOut}
                  className="flex w-full items-center gap-3 rounded-full px-4 py-2.5 text-sm font-medium text-muted transition-colors hover:bg-danger-soft hover:text-danger cursor-pointer"
                >
                  <LogOut size={18} />
                  Sign out
                </button>
              </div>
            </motion.div>
          </div>
        ) : null}
      </AnimatePresence>

      <main className="min-w-0 flex-1">
        <div className="mx-auto w-full max-w-[1280px] px-4 py-6 sm:px-8 sm:py-10">
          {children}
        </div>
      </main>
    </div>
  );
}
