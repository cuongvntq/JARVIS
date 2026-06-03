"use client";

import type { TodosCount } from "@/lib/types/api";

interface TodayStatsProps {
  count: TodosCount;
  onNavigate?: (section: string) => void;
}

interface StatCard {
  label: string;
  value: number;
  color: string;
  bg: string;
  section: string;
}

export default function TodayStats({ count, onNavigate }: TodayStatsProps) {
  const cards: StatCard[] = [
    {
      label: "HÔM NAY",
      value: count.today,
      color: "#00b4d8",
      bg: "rgba(0,180,216,0.10)",
      section: "todo",
    },
    {
      label: "QUÁ HẠN",
      value: count.overdue,
      color: "#ff4444",
      bg: "rgba(255,68,68,0.10)",
      section: "todo",
    },
    {
      label: "SẮP TỚI",
      value: count.upcoming,
      color: "#00e676",
      bg: "rgba(0,230,118,0.08)",
      section: "todo",
    },
  ];

  return (
    <div>
      <p className="text-[9px] font-semibold tracking-[0.2em] mb-3" style={{ color: "#3a6a7e" }}>
        CÔNG VIỆC
      </p>
      <div className="grid grid-cols-3 gap-2">
        {cards.map((c) => (
          <button
            key={c.label}
            type="button"
            onClick={() => onNavigate?.(c.section)}
            className="flex flex-col items-center justify-center rounded-lg py-3 px-2 transition-all hover:scale-105 hover:brightness-110 focus:outline-none"
            style={{ backgroundColor: c.bg, border: `1px solid ${c.color}22` }}
          >
            <span
              className="text-2xl font-bold tabular-nums leading-none"
              style={{ fontFamily: "var(--font-orbitron)", color: c.color }}
            >
              {c.value}
            </span>
            <span
              className="text-[8px] font-semibold tracking-[0.15em] mt-1.5"
              style={{ color: c.color, opacity: 0.7 }}
            >
              {c.label}
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}
