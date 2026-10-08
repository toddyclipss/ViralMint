import { useEffect, useState } from "react"
import { Box, Button, Stack, Typography } from "@mui/material"
import { useNavigate } from "react-router-dom"
import { IconMovie, IconArrowUpCircle } from "@tabler/icons-react"
import { GlassCard } from "../utils/glassFx"
import http from "../api/http"

/**
 * "Motion Graphics needs setting up" — one consistent card for every surface
 * that needs the engine, rendered in place of the page content.
 */
export default function MotionInstallGate({ onBack }) {
  const navigate = useNavigate()
  const [status, setStatus] = useState(null)   // null while checking

  useEffect(() => {
    let cancelled = false
    http.get("/api/settings/motion-graphics/status")
      .then((r) => { if (!cancelled) setStatus(r.data || {}) })
      .catch(() => { if (!cancelled) setStatus({}) })
    return () => { cancelled = true }
  }, [])

  const updating = !!status?.update_available
  const from = status?.installed_version
  const to = status?.hyperframes_version
  const mb = status?.approx_download_mb || 350

  return (
    <Box sx={{ height: "100%", display: "grid", placeItems: "center", p: 3 }}>
      <GlassCard sx={{ p: 4, textAlign: "center", maxWidth: 540, borderRadius: "20px" }}>
        <Box sx={{ display: "flex", justifyContent: "center", mb: 1.5 }}>
          {updating
            ? <IconArrowUpCircle size={44} stroke={1.8} color="var(--color-primary, #8b5cf6)" />
            : <IconMovie size={44} stroke={1.8} color="var(--color-primary, #8b5cf6)" />}
        </Box>
        <Typography variant="h6" component="h5" sx={{ fontWeight: 700, mb: 1 }}>
          {updating ? "Motion Graphics needs an update" : "Motion Graphics isn’t installed"}
        </Typography>
        <Typography variant="body2" sx={{ color: "text.secondary", mb: 3 }}>
          {updating ? (
            <>
              A newer engine ships with this version
              {from && to ? ` (${from} → ${to})` : ""}. The update is quick — it reuses
              the Node runtime already on disk, so it is not a full re-download.
            </>
          ) : (
            <>
              Render designed motion video — kinetic type, stat cards, lower thirds —
              entirely on this machine. It needs a one-time ~{mb}&nbsp;MB setup, which
              installs into your data folder and can be removed again at any time.
            </>
          )}
        </Typography>
        <Stack direction="row" spacing={1.5} justifyContent="center">
          {onBack && <Button variant="outlined" onClick={onBack} sx={{ borderRadius: "20px" }}>Back</Button>}
          <Button variant="contained" onClick={() => navigate("/settings#motion-graphics")} sx={{ borderRadius: "20px" }}>
            {updating ? "Update from Settings" : "Install from Settings"}
          </Button>
        </Stack>
      </GlassCard>
    </Box>
  )
}
