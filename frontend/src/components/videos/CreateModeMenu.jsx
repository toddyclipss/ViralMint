import { useState } from "react"
import { Typography, Menu, MenuItem, ListItemText, ListItemIcon } from "@mui/material"
import { IconWand, IconPhoto } from "@tabler/icons-react"
import http from "../../api/http"
import useAppStore from "../../store/appStore"

export default function CreateModeMenu({ anchorEl, onClose, sourceId, navigate }) {
  const showSnackbar = useAppStore((s) => s.showSnackbar)
  const [quickLoading, setQuickLoading] = useState(false)

  const handleQuickGenerate = async () => {
    onClose()
    setQuickLoading(true)
    try {
      await http.post(`/api/downloaded/${sourceId}/generate`, {
        aspect_ratio: "9:16",
        tts_provider: "edge_tts",
        caption_enabled: true,
        caption_style: "viral",
        music_enabled: true,
        music_genre: "lofi",
      })
      showSnackbar("Quick video generation started! Check the Generated tab.", "success")
    } catch (e) {
      showSnackbar(e.response?.data?.detail || `Quick generate failed: ${e.message}`, "error")
    } finally {
      setQuickLoading(false)
    }
  }

  return (
    <Menu anchorEl={anchorEl} open={Boolean(anchorEl)} onClose={onClose}
      slotProps={{ paper: { sx: { borderRadius: "16px", border: "1px solid", borderColor: "divider" } } }}>
      <MenuItem onClick={handleQuickGenerate} disabled={quickLoading}
        sx={{ borderBottom: 1, borderColor: "divider", mb: 0.5, borderRadius: "12px", mx: 0.5 }}>
        <ListItemIcon><IconWand size={18} stroke={1.8} color="#8b5cf6" /></ListItemIcon>
        <ListItemText
          primary={quickLoading ? "Starting..." : "Quick Stock Video"}
          secondary="One-click: Pexels stock footage + free voice + viral captions"
          primaryTypographyProps={{ fontWeight: 700, color: "primary.main" }}
          secondaryTypographyProps={{ fontSize: "0.7rem" }}
        />
      </MenuItem>
      <Typography variant="caption" sx={{ px: 2, py: 0.5, color: "text.disabled", display: "block" }}>
        Or customize in editor:
      </Typography>
      <MenuItem onClick={() => { onClose(); navigate(`/stock?source=${sourceId}`) }}
        sx={{ borderRadius: "12px", mx: 0.5 }}>
        <ListItemIcon><IconPhoto size={18} stroke={1.8} /></ListItemIcon>
        <ListItemText>Stock Video</ListItemText>
      </MenuItem>
    </Menu>
  )
}
