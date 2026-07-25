"use client";

import { motion } from "motion/react";

/**
 * The node-edge topology the design language is built on: property manager at the
 * centre, tenants feeding in, vendors fanning out, with traffic pulsing along the
 * links. Inline SVG — no external image, no CDN.
 */

interface Node {
  id: string;
  x: number;
  y: number;
  label: string;
}

const CENTER: Node = { id: "pm", x: 200, y: 200, label: "Dispatcher" };

const TENANTS: Node[] = [
  { id: "t1", x: 52, y: 96, label: "Tenant" },
  { id: "t2", x: 40, y: 210, label: "Tenant" },
  { id: "t3", x: 62, y: 320, label: "Tenant" },
];

const VENDORS: Node[] = [
  { id: "v1", x: 344, y: 108, label: "Plumbing" },
  { id: "v2", x: 358, y: 218, label: "Electrical" },
  { id: "v3", x: 332, y: 322, label: "HVAC" },
];

/** A packet travelling from `from` to `to`, looping with a stagger. */
function Packet({
  from,
  to,
  delay,
}: {
  from: { x: number; y: number };
  to: { x: number; y: number };
  delay: number;
}) {
  return (
    <motion.circle
      r={3}
      fill="#3a8fb9"
      initial={{ cx: from.x, cy: from.y, opacity: 0 }}
      animate={{
        cx: [from.x, to.x],
        cy: [from.y, to.y],
        opacity: [0, 1, 1, 0],
      }}
      transition={{
        duration: 2.4,
        delay,
        repeat: Infinity,
        repeatDelay: 1.6,
        ease: "easeInOut",
      }}
    />
  );
}

function NodeMark({ node, accent }: { node: Node; accent: string }) {
  return (
    <g>
      <rect
        x={node.x - 34}
        y={node.y - 14}
        width={68}
        height={28}
        rx={8}
        fill="#1a1d21"
        stroke={accent}
        strokeWidth={1.25}
      />
      <text
        x={node.x}
        y={node.y + 4}
        textAnchor="middle"
        fontSize={10}
        fill="#ffffff"
        opacity={0.85}
        fontFamily="var(--font-jetbrains-mono), monospace"
      >
        {node.label}
      </text>
    </g>
  );
}

export function NetworkPanel() {
  return (
    <svg
      viewBox="0 0 400 400"
      className="h-full w-full max-w-[26rem]"
      role="img"
      aria-label="Diagram: tenant reports flow into the dispatcher, which routes jobs out to vendors"
    >
      {/* Edges */}
      <g stroke="#667085" strokeWidth={1} opacity={0.45}>
        {[...TENANTS, ...VENDORS].map((node) => (
          <line
            key={node.id}
            x1={node.x}
            y1={node.y}
            x2={CENTER.x}
            y2={CENTER.y}
          />
        ))}
      </g>

      {/* Traffic: tenants -> dispatcher -> vendors */}
      {TENANTS.map((node, index) => (
        <Packet key={node.id} from={node} to={CENTER} delay={index * 0.55} />
      ))}
      {VENDORS.map((node, index) => (
        <Packet key={node.id} from={CENTER} to={node} delay={1.2 + index * 0.55} />
      ))}

      {/* Centre glow */}
      <motion.circle
        cx={CENTER.x}
        cy={CENTER.y}
        r={44}
        fill="#005691"
        animate={{ opacity: [0.12, 0.26, 0.12] }}
        transition={{ duration: 3.2, repeat: Infinity, ease: "easeInOut" }}
      />

      {TENANTS.map((node) => (
        <NodeMark key={node.id} node={node} accent="#667085" />
      ))}
      {VENDORS.map((node) => (
        <NodeMark key={node.id} node={node} accent="#3a8fb9" />
      ))}

      <rect
        x={CENTER.x - 46}
        y={CENTER.y - 18}
        width={92}
        height={36}
        rx={8}
        fill="#005691"
      />
      <text
        x={CENTER.x}
        y={CENTER.y + 4}
        textAnchor="middle"
        fontSize={11}
        fill="#ffffff"
        fontFamily="var(--font-jetbrains-mono), monospace"
      >
        {CENTER.label}
      </text>
    </svg>
  );
}
