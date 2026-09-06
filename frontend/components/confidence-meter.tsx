"use client";

import { motion } from "framer-motion";

export function ConfidenceMeter({ value }: { value: number }) {
  const color = value >= 85 ? "#3fbf7f" : value >= 60 ? "#e0b23f" : "#e0473f";
  return (
    <div className="flex items-center gap-3">
      <div className="h-2 w-40 rounded-full bg-ink-700 overflow-hidden">
        <motion.div
          className="h-full rounded-full"
          style={{ backgroundColor: color }}
          initial={{ width: 0 }}
          animate={{ width: `${value}%` }}
          transition={{ duration: 0.6, ease: "easeOut" }}
        />
      </div>
      <span className="tabular text-lg font-semibold" style={{ color }}>
        {value.toFixed(1)}%
      </span>
    </div>
  );
}
