"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { clearSession, getSession } from "@/lib/api";
import { useEffect, useState } from "react";

export function TopNav() {
  const pathname = usePathname();
  const router = useRouter();
  const [name, setName] = useState<string>("");
  const [role, setRole] = useState<string>("");

  useEffect(() => {
    const session = getSession();
    if (session) {
      setName(session.name);
      setRole(session.role);
    }
  }, []);

  const links = [
    { href: "/dashboard", label: "Control Center" },
    { href: "/proofs", label: "Proof Center" },
  ];

  return (
    <div className="sticky top-0 z-20 border-b border-line bg-ink-950/90 backdrop-blur px-6 py-3 flex items-center justify-between">
      <div className="flex items-center gap-8">
        <Link href="/dashboard" className="font-semibold tracking-wide text-sm">
          LEDGER<span className="text-accent">OS</span>
        </Link>
        <nav className="flex gap-4 text-sm">
          {links.map((l) => (
            <Link
              key={l.href}
              href={l.href}
              className={pathname?.startsWith(l.href) ? "text-accent" : "text-gray-400 hover:text-gray-200"}
            >
              {l.label}
            </Link>
          ))}
        </nav>
      </div>
      <div className="flex items-center gap-4 text-xs text-gray-400">
        <span>
          {name} <span className="text-gray-600">·</span> {role}
        </span>
        <button
          onClick={() => {
            clearSession();
            router.push("/login");
          }}
          className="text-gray-500 hover:text-gray-300"
        >
          Sign out
        </button>
      </div>
    </div>
  );
}
