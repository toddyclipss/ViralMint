import { Box, Typography } from "@mui/material"
import { IconRadar, IconDownload, IconMovie, IconUpload } from "@tabler/icons-react"

const actionConfig = {
  start_trend: { icon: <IconRadar size={16} stroke={1.8} />, label: "Finding Trends" },
  start_trends: { icon: <IconRadar size={16} stroke={1.8} />, label: "Finding Trends" },
  start_download: { icon: <IconDownload size={16} stroke={1.8} />, label: "Downloading" },
  start_generate: { icon: <IconMovie size={16} stroke={1.8} />, label: "Generating" },
  start_upload: { icon: <IconUpload size={16} stroke={1.8} />, label: "Uploading" },
}

export default function ActionBlock({ action }) {
  if (!action || !action.type) return null
  const config = actionConfig[action.type] || { icon: <IconRadar size={16} stroke={1.8} />, label: action.type }

  return (
    <Box sx={{
      display: "flex", alignItems: "center", gap: 1,
      px: 1.5, py: 0.75,
      bgcolor: "rgba(139, 92, 246, 0.08)",
      border: 1, borderColor: "rgba(139, 92, 246, 0.25)",
      borderRadius: "12px", mt: 0.5,
      color: "primary.main", fontSize: "0.85rem",
    }}>
      {config.icon}
      <Typography variant="body2" sx={{ color: "primary.main", fontWeight: 500 }}>{config.label}</Typography>
      {action.niche && <Typography variant="body2" sx={{ color: "text.secondary" }}>-- {action.niche}</Typography>}
    </Box>
  )
}
