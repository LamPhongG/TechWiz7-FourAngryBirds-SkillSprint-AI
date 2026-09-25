
function SkeletonBlock({ width = "100%", height = "14px", radius = "6px", className = "" }) {
  return (
    <span
      className={`skeleton ${className}`}
      style={{ width, height, borderRadius: radius, display: "block" }}
    />
  );
}

export function SkeletonTableRows({ rows = 5, cols = 5 }) {
  return (
    <>
      {Array.from({ length: rows }).map((_, i) => (
        <tr key={i}>
          {Array.from({ length: cols }).map((_, j) => (
            <td key={j} style={{ padding: "14px 10px" }}>
              <SkeletonBlock width={j === 0 ? "80%" : "60%"} height="11px" />
            </td>
          ))}
        </tr>
      ))}
    </>
  );
}
