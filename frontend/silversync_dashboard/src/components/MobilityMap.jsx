export default function MobilityMap({ heatmap, movement_path }) {
  if (!heatmap || Object.keys(heatmap).length === 0) {
    return <p>No mobility data.</p>;
  }

  const cells = Object.entries(heatmap).map(([key, count]) => {
    const [x, y] = key.split(",").map(Number);
    return { x, y, count };
  });

  const GRID_SIZE = 600;

  // collect raw coordinates
  const xs = cells.map(c => c.x);
  const ys = cells.map(c => c.y);

  // include movement coords in scaling to avoid distortion
  if (movement_path?.length > 0) {
    xs.push(...movement_path.map(p => p.x));
    ys.push(...movement_path.map(p => p.y));
  }

  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);

  const maxCount = Math.max(...cells.map(c => c.count));

  function scale(val, min, max) {
    if (max === min) return GRID_SIZE / 2;
    return ((val - min) / (max - min)) * GRID_SIZE;
  }

  // current position (last data point)
  const current = movement_path && movement_path.length > 0
    ? movement_path[movement_path.length - 1]
    : null;

  return (
    <div style={{ width: GRID_SIZE, margin: "auto" }}>
      <h3 style={{ textAlign: "center", marginBottom: "10px" }}>Mobility Map</h3>

      <div
        style={{
          position: "relative",
          width: GRID_SIZE,
          height: GRID_SIZE,
          background: "#0b1221",
          borderRadius: "8px",
          overflow: "hidden",
          border: "2px solid #222",
        }}
      >
        {/* Heatmap Squares */}
        {cells.map((c, i) => {
          const sx = scale(c.x, minX, maxX);
          const sy = GRID_SIZE - scale(c.y, minY, maxY);

          return (
            <div
              key={i}
              style={{
                position: "absolute",
                left: sx,
                top: sy,
                width: 14,
                height: 14,
                borderRadius: "2px",
                backgroundColor: `rgba(0, 150, 255, ${c.count / maxCount})`,
                border: "1px solid rgba(255,255,255,0.15)",
                transform: "translate(-50%, -50%)",
              }}
            />
          );
        })}

        {/* Current Position Marker */}
        {current && (
          <div
            style={{
              position: "absolute",
              left: scale(current.x, minX, maxX),
              top: GRID_SIZE - scale(current.y, minY, maxY),
              width: 14,
              height: 14,
              borderRadius: "50%",
              backgroundColor: "limegreen",
              border: "2px solid white",
              transform: "translate(-50%, -50%)",
              boxShadow: "0 0 8px rgba(0,255,0,0.9)",
            }}
          />
        )}
      </div>
    </div>
  );
}
