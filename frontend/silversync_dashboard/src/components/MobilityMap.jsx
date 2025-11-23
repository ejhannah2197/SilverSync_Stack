import { useEffect, useState } from "react";

export default function MobilityMap({ heatmap, movement_path, events }) {
  const GRID_SIZE = 600; // size of display area
  const BUCKET = 20;

  // Convert heatmap entries to objects
  const cells = Object.entries(heatmap).map(([key, count]) => {
    const [x, y] = key.split(",").map(Number);
    return { x, y, count };
  });

  if (cells.length === 0) {
    return <p>No mobility data available.</p>;
  }

  const maxCount = Math.max(...cells.map(c => c.count));

  // Scaling boundaries
  const xs = cells.map(c => c.x);
  const ys = cells.map(c => c.y);

  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);

  const scale = (val, min, max) =>
    ((val - min) / (max - min)) * GRID_SIZE;

  // -------------------------------
  // Movement Animation State
  // -------------------------------
  const [index, setIndex] = useState(0);

  useEffect(() => {
    if (!movement_path || movement_path.length === 0) return;

    const timer = setInterval(() => {
      setIndex(i => (i + 1) % movement_path.length);
    }, 200); // speed of animation

    return () => clearInterval(timer);
  }, [movement_path]);

  const currentPos = movement_path[index];

  return (
    <div
      style={{
        width: GRID_SIZE,
        height: GRID_SIZE,
        position: "relative",
        backgroundColor: "#111",
        border: "2px solid #333",
      }}
    >
      {/* HEATMAP CELLS */}
      {cells.map((c, i) => (
        <div
          key={i}
          style={{
            position: "absolute",
            left: `${scale(c.x, minX, maxX)}px`,
            top: `${GRID_SIZE - scale(c.y, minY, maxY)}px`,
            width: "14px",
            height: "14px",
            backgroundColor: `rgba(0, 150, 255, ${c.count / maxCount})`,
            border: "1px solid rgba(255,255,255,0.1)",
          }}
        />
      ))}

      {/* EVENT MARKERS */}
      {events.map((ev, i) => (
        <div
          key={`ev-${i}`}
          title={`Event ${ev.event_id}`}
          style={{
            position: "absolute",
            left: `${scale(ev.x_event, minX, maxX)}px`,
            top: `${GRID_SIZE - scale(ev.y_event, minY, maxY)}px`,
            width: "20px",
            height: "20px",
            backgroundColor: "red",
            borderRadius: "50%",
            border: "2px solid white",
          }}
        />
      ))}

      {/* ANIMATED POSITION DOT */}
      {currentPos && (
        <div
          style={{
            position: "absolute",
            left: `${scale(currentPos.x, minX, maxX)}px`,
            top: `${GRID_SIZE - scale(currentPos.y, minY, maxY)}px`,
            width: "14px",
            height: "14px",
            backgroundColor: "#00ff88",
            borderRadius: "50%",
            boxShadow: "0 0 8px #00ff88",
          }}
        />
      )}
    </div>
  );
}
