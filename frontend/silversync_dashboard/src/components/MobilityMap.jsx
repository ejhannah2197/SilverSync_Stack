export default function MobilityMap({ heatmap }) {
  if (!heatmap || Object.keys(heatmap).length === 0) {
    return <p>No mobility data.</p>;
  }

  const cells = Object.entries(heatmap).map(([key, count]) => {
    const [x, y] = key.split(",").map(Number);
    return { x, y, count };
  });

  const GRID_SIZE = 600;

  // ----- Compute the min/max of coordinates -----
  const xs = cells.map(c => c.x);
  const ys = cells.map(c => c.y);

  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);

  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);

  const maxCount = Math.max(...cells.map(c => c.count));

  // ----- Convert real coordinates → screen coords -----
  function scale(val, min, max) {
    if (max === min) return GRID_SIZE / 2;
    return ((val - min) / (max - min)) * GRID_SIZE;
  }

  return (
    <div style={{ width: GRID_SIZE, height: GRID_SIZE, position: "relative", margin: "auto" }}>
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
        {cells.map((c, i) => {
          const sx = scale(c.x, minX, maxX);
          const sy = GRID_SIZE - scale(c.y, minY, maxY); // flip Y axis

          const opacity = c.count / maxCount;

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
                backgroundColor: `rgba(0, 150, 255, ${opacity})`,
                border: "1px solid rgba(255,255,255,0.15)",
                transform: "translate(-50%, -50%)",
              }}
            />
          );
        })}
      </div>
    </div>
  );
}
